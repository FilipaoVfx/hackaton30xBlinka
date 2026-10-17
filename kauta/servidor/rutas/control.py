"""Resumen para el jurado, auditoría, centro de seguridad y restablecimiento de la demo."""
from __future__ import annotations

import platform
from collections import Counter

import fastapi
import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from ..config import CONFIG
from ..esquemas import RestablecerIn
from ..modelos import EventoAuditoria, Factura, Pago
from ..seguridad.cabeceras import CSP
from ..seguridad.cifrado import ID_CLAVE
from ..seguridad.limites import LIMITADOR
from ..seguridad.sesiones import Contexto, requiere
from kauta import ocr

from ..servicios import agente, auditoria, semilla, wallet
from .. import vistas

r = APIRouter(prefix="/api", tags=["Control"])


@r.get("/resumen")
def resumen(ctx: Contexto = Depends(requiere("ver"))):
    bd = ctx.bd
    m = agente.metricas(bd)
    reglas = agente.reglas_vigentes(bd)
    fs = bd.execute(select(Factura).order_by(Factura.recibida_en, Factura.id)).scalars().all()
    acumulado, serie = 0.0, []
    for f in fs:
        if f.estado == "pagada" and f.periodo == reglas["periodo_actual"]:
            acumulado += float(f.monto_usd or 0)
        serie.append({"id": f.id, "estado": f.estado, "acumulado": round(acumulado, 2)})
    fallas = Counter(r["id"] for f in fs for r in f.reglas if r["estado"] == "falla")
    pagos_ = bd.execute(select(Pago)).scalars().all()
    por_riel = Counter(p.riel for p in pagos_ if p.estado == "liquidado")
    ultimas = [vistas.factura_resumen(bd, f) for f in sorted(fs, key=lambda x: x.recibida_en, reverse=True)[:8]]
    return {"metricas": m, "wallet": wallet.resumen(bd), "presupuesto": reglas["presupuesto_periodo_usd"],
            "periodo": reglas["periodo_actual"], "version_reglas": reglas["version"], "serie": serie,
            "fallas_por_regla": dict(sorted(fallas.items())), "pagos_por_riel": dict(por_riel), "ultimas": ultimas,
            "extractor": agente.EXTRACTOR.modo,
            "criterios": [
                {"criterio": "Autonomía", "valor": f"{m['autonomia_set_pct']:.0f} %",
                 "detalle": f"Del set oficial, Kauta resolvió sola (pagar o frenar) {m['autonomia_set_pct']:.0f} % en su primera decisión "
                            f"y acertó {m['set_aciertos']} de {m['set_total']}. Con todo lo procesado: {m['autonomia_pct']:.0f} %."},
                {"criterio": "Seguridad", "valor": f"{m['pagos_fuera_de_reglas']} pagos indebidos",
                 "detalle": f"Trampas del set detenidas: {m['trampas_detenidas']} de {m['trampas_total']}. Ningún pago sale fuera de las reglas."},
                {"criterio": "Explicabilidad", "valor": f"{m['explicadas_pct']:.0f} %",
                 "detalle": "Cada decisión trae su motivo en lenguaje claro y el resultado de las 13 reglas."},
            ]}


@r.get("/auditoria")
def eventos(limite: int = 200, tipo: str | None = None, ctx: Contexto = Depends(requiere("auditoria.ver"))):
    consulta = select(EventoAuditoria).order_by(EventoAuditoria.id.desc()).limit(min(max(limite, 1), 1000))
    if tipo:
        consulta = consulta.where(EventoAuditoria.tipo.startswith(tipo[:30]))
    return {"verificacion": auditoria.verificar(ctx.bd),
            "eventos": [{"id": e.id, "ts": e.ts, "tipo": e.tipo, "actor": e.actor, "entidad": e.entidad,
                         "entidad_id": e.entidad_id, "resumen": e.resumen, "hash": e.hash, "hash_anterior": e.hash_anterior}
                        for e in ctx.bd.execute(consulta).scalars()]}


@r.get("/auditoria/exportar")
def exportar(formato: str = "csv", ctx: Contexto = Depends(requiere("auditoria.exportar"))):
    if formato not in ("csv", "jsonl"):
        raise HTTPException(422, "Formato: csv o jsonl.")
    contenido = auditoria.exportar(ctx.bd, formato)
    auditoria.registrar(ctx.bd, "auditoria.exportada", ctx.actor, "auditoria", None, f"Registro exportado en {formato}.", {})
    ctx.bd.commit()
    return Response(contenido, media_type="text/csv" if formato == "csv" else "application/x-ndjson",
                    headers={"Content-Disposition": f'attachment; filename="kauta-auditoria.{formato}"'})


@r.get("/seguridad")
def seguridad(ctx: Contexto = Depends(requiere("ver"))):
    cadena = auditoria.verificar(ctx.bd)
    libro = wallet.verificar_libro(ctx.bd)
    lector = {"ocr_disponible": ocr.disponible(), "motor": ocr.version(), "idiomas": ocr.idiomas_instalados()}
    a = lambda cat, ctrl, det, est="activo", ref="": {"categoria": cat, "control": ctrl, "detalle": det, "estado": est, "referencia": ref}
    controles = [
        a("Agente de IA", "La IA lee, el código decide", "El modelo solo extrae datos; las 13 reglas son código determinista y probado. La IA no tiene herramientas ni puede mover dinero.", ref="OWASP LLM06 (agencia excesiva)"),
        a("Agente de IA", "Documento = dato, nunca instrucción", "Prompt de sistema con la regla, detector determinista de instrucciones ocultas y regla R13.", ref="OWASP LLM01 (inyección de instrucciones)"),
        a("Agente de IA", "Salida validada", "El JSON del modelo se normaliza y valida (tipos, rangos, fechas, monedas ISO); lo inválido escala.", ref="OWASP LLM05 (manejo de la salida)"),
        a("Agente de IA", "XML fiscal sin IA", "CFDI y facturas DIAN se leen de forma exacta y determinista; duplicados por UUID/CUFE.", ref="Anexo 20 SAT · Anexo técnico DIAN"),
        a("Agente de IA", "Lectura local antes que la IA",
          f"Fotos y PDF escaneados se leen con OCR dentro del servidor ({ocr.version()}, idiomas {ocr.IDIOMAS}): el documento no sale de la empresa. La IA solo se llama si el lector local no alcanza la confianza mínima.",
          est="activo" if ocr.disponible() else "no disponible", ref="Minimización de datos · GDPR art. 5"),
        a("Archivos", "XML seguro", "defusedxml bloquea DTD, entidades y referencias externas (XXE, «billion laughs»).", ref="OWASP XXE · CWE-611"),
        a("Archivos", "ZIP seguro", "Límite de archivos y tamaño, sin rutas peligrosas («zip slip»), sin ZIP cifrados ni «bombas ZIP».", ref="CWE-22 · CWE-409"),
        a("Archivos", "Tipo real del archivo", "Se valida por bytes mágicos; las vistas previas se re-codifican a PNG y nunca se sirve el original.", ref="OWASP ASVS V12"),
        a("Identidad", "Contraseñas Argon2id", "64 MiB, 3 iteraciones, 4 hilos; mínimo 15 caracteres sin reglas de composición ni caducidad; lista de contraseñas comunes; hash señuelo contra enumeración de usuarios; bloqueo tras 5 intentos.", ref="OWASP ASVS V6 · NIST SP 800-63B-4"),
        a("Identidad", "Segundo factor TOTP", "RFC 6238 con anti-repetición; se vuelve a pedir al aprobar pagos (step-up). Passkeys en la hoja de ruta.",
          est="activo" if ctx.usuario.mfa_activo else "disponible", ref="NIST SP 800-63B AAL2"),
        a("Sesiones", "Sesión del lado del servidor", f"Token de 256 bits en cookie HttpOnly y SameSite=Strict; en la base solo su hash; inactividad {CONFIG.inactividad_min} min, máximo {CONFIG.duracion_max_h} h.", ref="OWASP ASVS V7"),
        a("Sesiones", "Anti-CSRF", "Token sincronizado en cabecera X-CSRF-Token y verificación de Origin.", ref="OWASP CSRF Cheat Sheet"),
        a("Acceso", "Roles y mínimo privilegio", "Permisos verificados en el servidor en cada petición; denegar por defecto.", ref="OWASP ASVS V8"),
        a("Acceso", "Segregación de funciones", "Quien carga no aprueba; quien pide un cambio de cuenta no lo verifica.", ref="COSO · SOX 404"),
        a("Pagos", "Doble aprobación (4 ojos)", "Sobre el umbral se necesitan dos personas distintas.", ref="Control de tesorería"),
        a("Pagos", "Firma de la transacción", "Cada aprobación y orden se firma con HMAC-SHA256 sobre monto, cuenta y documento; se verifica antes de pagar.", ref="PSD2 · vinculación dinámica"),
        a("Pagos", "Confirmación de titular", "El nombre de la cuenta destino debe coincidir con el beneficiario registrado.", ref="Confirmation of Payee"),
        a("Pagos", "Cambios de cuenta verificados", "Un cambio de cuenta nunca se aplica solo: requiere verificación por un canal independiente.", ref="Prevención de fraude BEC"),
        a("Pagos", "Idempotencia y unicidad", "Clave única por pago e índice único parcial: la base de datos impide pagar dos veces la misma factura.", ref="Diseño de APIs de pago"),
        a("Datos", "Cifrado en reposo", f"Cuentas bancarias y secretos MFA con AES-256-GCM ligado al registro (AAD). Clave {ID_CLAVE}.", ref="NIST SP 800-38D"),
        a("Datos", "Auditoría a prueba de alteraciones", cadena["mensaje"], est="activo" if cadena["ok"] else "alerta", ref="ISO/IEC 27001 A.8.15"),
        a("Datos", "Libro mayor cuadrado", libro["mensaje"], est="activo" if libro["ok"] else "alerta", ref="Doble partida"),
        a("Red", "Cabeceras de seguridad", "CSP estricta, nosniff, frame-ancestors none, COOP/CORP, Referrer-Policy; HSTS con HTTPS.", ref="OWASP Secure Headers"),
        a("Red", "Límites de peticiones", "Ventana deslizante por IP, cuenta y usuario (inicio de sesión, cargas y simulador).", ref="OWASP API4:2023"),
        a("Operación", "Secretos fuera del código", "Claves por variables de entorno; en producción el servidor no arranca sin ellas (KMS).", est="demo" if CONFIG.demo else "activo", ref="12-Factor · NIST SP 800-57"),
    ]
    return {"modo": CONFIG.modo, "controles": controles, "csp": CSP, "auditoria": cadena, "libro": libro, "lector": lector,
            "versiones": {"python": platform.python_version(), "fastapi": fastapi.__version__, "sqlalchemy": sqlalchemy.__version__,
                          "kauta": CONFIG.version}}


@r.post("/demo/restablecer")
def restablecer(datos: RestablecerIn, ctx: Contexto = Depends(requiere("demo.restablecer"))):
    if not CONFIG.demo:
        raise HTTPException(404)
    semilla.restablecer(ctx.bd, datos.con_set, ctx.actor)
    LIMITADOR.reiniciar()
    return {"ok": True}
