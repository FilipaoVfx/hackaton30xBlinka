"""
El agente Kauta en el servidor: extracción (IA solo si hace falta) + motor de reglas determinista +
pago por la wallet + registro de auditoría. Todo se guarda en la base de datos.

Ciclo de una factura:
  1. Se lee el documento (XML fiscal exacto, extracción verificada o IA) y se valida.
  2. El motor decide con las reglas vigentes: pagar, frenar o escalar.
  3. Si es «pagar», el pago sale solo por la wallet (con sus propios controles).
  4. Si es «escalar», Kauta pregunta a una persona; si supera el umbral, se necesitan DOS personas.
  5. Al aprobar, el motor vuelve a revisar las reglas duras: ninguna aprobación rompe saldo,
     duplicados, bloqueos ni el máximo por pago.
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kauta import motor
from kauta.extractor import ExtraccionNoDisponible, ExtractorReferencia

from ..config import RAIZ, VAR
from ..modelos import (Aprobacion, Beneficiario, CambioCuenta, Factura, Pago, Usuario, VersionReglas, ahora)
from ..seguridad import firma
from ..seguridad.cifrado import cifrar
from . import BLOQUEO, auditoria, costos, pagos, wallet

ESTADO = {"pagar": "pagada", "frenar": "frenada", "escalar": "pendiente"}
ARCHIVOS = VAR / "archivos"


class ErrorNegocio(ValueError):
    """Error explicable para la persona (se devuelve como 409/422 con el mensaje)."""


# ---------------------------------------------------------------------------
# Extractor del servidor: XML y set de referencia sin IA; IA para documentos nuevos si hay clave
# ---------------------------------------------------------------------------
class ExtractorServidor:
    def __init__(self) -> None:
        self.ref = ExtractorReferencia()
        self.ia = None
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                from kauta.extractor import ExtractorIA
                self.ia = ExtractorIA()
            except Exception:
                self.ia = None

    @property
    def modo(self) -> str:
        return f"IA activa ({self.ia.modelo})" if self.ia else "Demo: XML fiscal y set de referencia (sin clave de IA)"

    def extraer(self, nombre: str, datos: bytes) -> dict[str, Any]:
        try:
            return self.ref.extraer(nombre, datos)
        except ExtraccionNoDisponible:
            if self.ia:
                return self.ia.extraer(nombre, datos)
            raise ErrorNegocio("Este documento no es XML fiscal ni está en el set de prueba. Para leer PDF, imágenes o "
                               "correos nuevos, configure ANTHROPIC_API_KEY en el servidor (modo IA).")


EXTRACTOR = ExtractorServidor()


# ---------------------------------------------------------------------------
# Datos para el motor
# ---------------------------------------------------------------------------
def reglas_vigentes(bd: Session) -> dict[str, Any]:
    v = bd.execute(select(VersionReglas).order_by(VersionReglas.version.desc()).limit(1)).scalar_one()
    return {**v.parametros, "version": v.version}


def beneficiarios_motor(bd: Session) -> list[dict[str, Any]]:
    return [{"id": b.id, "nombre": b.nombre, "id_fiscal": b.id_fiscal, "pais": b.pais, "tipo_persona": b.tipo_persona,
             "categoria": b.categoria, "contrato": b.contrato, "cuenta_registrada": b.cuenta_ultimos4,
             "estado": b.estado, "motivo_bloqueo": b.motivo_bloqueo}
            for b in bd.execute(select(Beneficiario).order_by(Beneficiario.id)).scalars()]


def historial(bd: Session, excluir: str | None = None) -> list[dict[str, Any]]:
    return [{"factura_id": f.id, "beneficiario_clave": f.beneficiario_clave, "numero_factura": f.numero,
             "periodo": f.periodo, "estado": f.estado, "monto_usd": float(f.monto_usd) if f.monto_usd is not None else None,
             "hashes": f.hashes, "id_fiscal_unico": f.id_fiscal_unico}
            for f in bd.execute(select(Factura).order_by(Factura.recibida_en, Factura.id)).scalars() if f.id != excluir]


def periodos_abiertos(reglas: dict[str, Any]) -> list[str]:
    """Periodo actual y el siguiente: los únicos que la tesorería automática fondea."""
    a, m = (int(x) for x in reglas["periodo_actual"].split("-"))
    return [reglas["periodo_actual"], f"{a + (m // 12)}-{m % 12 + 1:02d}"]


def nuevo_id(bd: Session, nombre: str, origen: str) -> str:
    pref = Path(nombre).name.split("_")[0]
    if re.fullmatch(r"[FS]\d{2}", pref) and not bd.get(Factura, pref):
        return pref
    base = "SIM" if origen == "simulador" else "N"
    n = 1
    while bd.get(Factura, f"{base}{n:03d}"):
        n += 1
    return f"{base}{n:03d}"


def _dec(v: Any) -> Decimal | None:
    return Decimal(str(v)).quantize(Decimal("0.01")) if v is not None else None


def guardar_archivo(nombre: str, datos: bytes) -> str:
    """Los archivos se guardan con nombre aleatorio derivado de su huella, fuera de la carpeta web."""
    ARCHIVOS.mkdir(parents=True, exist_ok=True)
    ext = re.sub(r"[^a-z0-9.]", "", Path(nombre).suffix.lower())[:6] or ".bin"
    ruta = ARCHIVOS / (hashlib.sha256(datos).hexdigest() + ext)
    if not ruta.exists():
        ruta.write_bytes(datos)
    return str(ruta)


# ---------------------------------------------------------------------------
# Procesar una factura
# ---------------------------------------------------------------------------
def procesar_archivo(bd: Session, nombre: str, datos: bytes, origen: str, actor: str, cargada_por: str,
                     forzar_pago: str | None = None) -> Factura:
    r = EXTRACTOR.extraer(nombre, datos)
    return registrar(bd, nombre, r, origen, actor, cargada_por, ruta=guardar_archivo(nombre, datos), forzar_pago=forzar_pago)


def registrar(bd: Session, nombre: str, r: dict[str, Any], origen: str, actor: str, cargada_por: str,
              ruta: str | None = None, forzar_pago: str | None = None, factura_id: str | None = None,
              riel: str | None = None, confirmar: bool = True) -> Factura:
    with BLOQUEO:
        fid = factura_id or nuevo_id(bd, nombre, origen)
        reglas = reglas_vigentes(bd)
        bens = beneficiarios_motor(bd)
        ext = r["extraccion"]
        ben, _ = motor.buscar_beneficiario(ext, bens)
        periodo = motor.periodo_de(ext, reglas)
        if wallet.asegurar_fondeo(bd, periodo, Decimal(str(reglas["presupuesto_periodo_usd"])), periodos_abiertos(reglas)):
            auditoria.registrar(bd, "wallet.fondeo_periodo", "Tesorería automática", "wallet", "cxp",
                                f"Se fondeó la sub-wallet para {periodo} con USD {reglas['presupuesto_periodo_usd']:,}.", {})
        t0 = datetime.now(timezone.utc)
        d = motor.evaluar({"factura_id": fid, "extraccion": ext, "hashes": r["hashes"]}, reglas, bens, historial(bd))
        ms = round((datetime.now(timezone.utc) - t0).total_seconds() * 1000, 1)
        umbral = Decimal(str(reglas["umbral_aprobacion_usd"]))
        requeridas = 0 if d.decision != "escalar" else (2 if Decimal(str(d.monto_usd or 0)) > umbral else 1)
        lista = [asdict(x) for x in d.reglas]
        f = Factura(id=fid, archivo=nombre, canal=r["canal"], origen=origen, ruta_archivo=ruta,
                    hash_documento=r["hashes"][0], hashes=r["hashes"], cargada_por=cargada_por, extraccion=ext,
                    texto=(r.get("texto") or "")[:20000], metodo_lectura=ext.get("metodo_lectura") or "ia",
                    modelo=r.get("modelo") or "", beneficiario_id=d.beneficiario_id,
                    beneficiario_nombre=d.beneficiario_nombre or "Sin nombre", beneficiario_clave=motor.clave_beneficiario(ben, ext),
                    numero=ext.get("numero_factura"), id_fiscal_unico=ext.get("id_fiscal_unico"), monto=_dec(d.monto),
                    moneda=d.moneda, monto_usd=_dec(d.monto_usd), periodo=d.periodo or reglas["periodo_actual"],
                    fecha_vencimiento=ext.get("fecha_vencimiento"), decision=d.decision, decision_inicial=d.decision,
                    estado=ESTADO[d.decision], motivo=d.motivo, motivo_inicial=d.motivo, reglas=lista, reglas_iniciales=lista,
                    version_reglas=d.version_reglas or reglas["version"], aprobaciones_requeridas=requeridas)
        bd.add(f)
        bd.flush()
        costos.registrar_lectura(bd, f, float(reglas["confianza_minima"]))
        auditoria.registrar(bd, "factura.decision", actor, "factura", fid, d.motivo[:400],
                            {"decision": d.decision, "monto_usd": d.monto_usd, "beneficiario": f.beneficiario_nombre,
                             "metodo_lectura": f.metodo_lectura, "modelo": f.modelo, "hash_documento": f.hash_documento,
                             "version_reglas": f.version_reglas, "duracion_ms": ms,
                             "reglas": {x["id"]: x["estado"] for x in lista}})
        if d.decision == "pagar":
            _pagar_o_escalar(bd, f, reglas, actor, forzar_pago, riel)
        r07 = next((x for x in lista if x["id"] == "R07" and x["estado"] == "falla"), None)
        if r07 and f.beneficiario_id and (ext.get("cuenta_destino") or ""):
            _solicitar_cambio_cuenta(bd, f, ext["cuenta_destino"])
        if confirmar:
            bd.commit()
        return f


def _pagar_o_escalar(bd: Session, f: Factura, reglas: dict[str, Any], actor: str, forzar: str | None,
                     riel: str | None = None) -> Pago | None:
    """El motor dijo «pagar»; los controles del pago aún pueden detenerlo (defensa en profundidad)."""
    try:
        with bd.begin_nested():
            return pagos.crear_y_ejecutar(bd, f, reglas, actor, forzar=forzar, riel=riel)
    except ValueError as e:
        f.decision, f.estado = "escalar", "pendiente"
        if f.aprobaciones_requeridas == 0:
            f.decision_inicial = "escalar"
            f.aprobaciones_requeridas = 1
        f.motivo = f"Escalada · Control del pago: {e} El motor aprobó, pero el pago no sale hasta que una persona lo revise."
        if f.motivo_inicial.startswith("Pagada"):
            f.motivo_inicial = f.motivo
        auditoria.registrar(bd, "pago.bloqueado", "Agente Kauta", "factura", f.id, str(e)[:300], {})
        return None


def _solicitar_cambio_cuenta(bd: Session, f: Factura, ultimos4: str) -> None:
    pendiente = bd.execute(select(CambioCuenta).where(CambioCuenta.beneficiario_id == f.beneficiario_id,
                                                      CambioCuenta.estado == "pendiente")).scalar_one_or_none()
    if pendiente:
        return
    banco = "Banca Aurora (simulado)"
    m = re.search(r"(Banca|Banco)\s+[A-ZÁÉÍÓÚa-záéíóúñ ]+\(simulado\)", f.texto or "")
    if m:
        banco = m.group(0)
    c = CambioCuenta(beneficiario_id=f.beneficiario_id, factura_id=f.id, banco_nuevo=banco,
                     cuenta_nueva_cifrada=cifrar("0" * 8 + ultimos4[-4:], aad=f"cambio:{f.beneficiario_id}"),
                     ultimos4_nuevos=ultimos4[-4:], origen=f"Factura {f.id} ({f.canal})",
                     solicitada_por="Agente Kauta (detectado en la factura)")
    bd.add(c)
    bd.flush()
    auditoria.registrar(bd, "cuenta.cambio_solicitado", "Agente Kauta", "beneficiario", f.beneficiario_id,
                        f"La factura {f.id} pide pagar a ···{ultimos4[-4:]}; queda pendiente de verificación independiente.",
                        {"factura": f.id, "solicitud": c.id})


# ---------------------------------------------------------------------------
# Decisiones humanas
# ---------------------------------------------------------------------------
def aprobar(bd: Session, fid: str, u: Usuario, comentario: str, correcciones: dict[str, Any] | None,
            con_mfa: bool) -> dict[str, Any]:
    with BLOQUEO:
        f = bd.get(Factura, fid)
        if not f:
            raise ErrorNegocio("La factura no existe.")
        if f.estado != "pendiente":
            raise ErrorNegocio(f"Solo se aprueban facturas pendientes (estado actual: {f.estado}).")
        if f.cargada_por == u.correo:
            raise ErrorNegocio("Segregación de funciones: quien cargó la factura no puede aprobarla.")
        previas = [a for a in f.aprobaciones if a.accion == "aprobar"]
        if any(a.usuario_id == u.id for a in previas):
            raise ErrorNegocio("Usted ya aprobó esta factura: el doble control exige que la segunda aprobación sea de otra persona.")
        if (f.excluir_firmante == u.correo and len(previas) + 1 >= f.aprobaciones_requeridas
                and not any(a.usuario_id != u.id for a in previas)):
            raise ErrorNegocio("Usted cambió las reglas o los datos que reevaluaron esta factura: la firma debe ser de otra persona.")
        if not (comentario or "").strip():
            raise ErrorNegocio("Escriba por qué aprueba: toda decisión humana debe quedar explicada.")
        reglas = reglas_vigentes(bd)
        bens = beneficiarios_motor(bd)
        ext = dict(f.extraccion)
        corr = {k: v for k, v in (correcciones or {}).items() if v not in (None, "")}
        if corr:
            ext["confianza"] = dict(ext.get("confianza") or {})
            for k, v in corr.items():
                if k in ("monto", "horas"):
                    v = float(v)
                ext[k] = v
                ext["confianza"][k] = 1.0
            ext["validaciones"] = [v for v in ext.get("validaciones") or [] if v.get("campo") != "qr_total"]
        if not ext.get("fecha_vencimiento") and ext.get("metodo_lectura") != "xml_fiscal":
            raise ErrorNegocio("Confirma la fecha de vencimiento del documento antes de aprobar.")
        d = motor.evaluar({"factura_id": fid, "extraccion": ext, "hashes": f.hashes}, reglas, bens, historial(bd, excluir=fid))
        duras = d.fallas("frenar")
        if duras:
            auditoria.registrar(bd, "aprobacion.bloqueada", f"{u.nombre} ({u.cargo})", "factura", fid,
                                f"Intento de aprobación bloqueado por regla dura {duras[0].id}: {duras[0].detalle}"[:400],
                                {"reglas": [r.id for r in duras]})
            bd.commit()
            raise ErrorNegocio(f"La aprobación no procede por una regla dura ({duras[0].id}): {duras[0].detalle}")
        if corr:
            f.extraccion = ext
            f.fecha_vencimiento = ext.get("fecha_vencimiento")
            f.monto, f.moneda, f.monto_usd = _dec(d.monto), d.moneda, _dec(d.monto_usd)
        nivel = len(previas) + 1
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ben = bd.get(Beneficiario, f.beneficiario_id) if f.beneficiario_id else None
        datos = pagos.datos_aprobacion(f, ben.id if ben else None, ben.cuenta_ultimos4 if ben else "", u.id, nivel, "aprobar", ts)
        revisadas = [r["id"] for r in f.reglas if r["estado"] == "falla" and r["efecto"] == "escalar"]
        a = Aprobacion(factura_id=fid, usuario_id=u.id, usuario_nombre=u.nombre, nivel=nivel, accion="aprobar",
                       comentario=comentario.strip()[:1000], correcciones=corr, reglas_revisadas=revisadas,
                       datos_firmados=datos, firma=firma.firmar(datos), con_mfa=con_mfa)
        bd.add(a)
        bd.flush()
        costos.registrar_revision(bd, f, a, u.correo)
        auditoria.registrar(bd, "aprobacion", f"{u.nombre} ({u.cargo})", "factura", fid,
                            f"Aprobación {nivel} de {f.aprobaciones_requeridas} · «{comentario.strip()[:160]}»",
                            {"firma": a.firma[:16], "con_mfa": con_mfa, "correcciones": corr, "reglas_revisadas": revisadas})
        if nivel < f.aprobaciones_requeridas:
            bd.commit()
            return {"ok": True, "completa": False, "mensaje": f"Aprobación {nivel} de {f.aprobaciones_requeridas} registrada. "
                    "El monto supera el umbral: falta la aprobación de otra persona (doble control)."}
        quienes = " y ".join(x.usuario_nombre for x in [*previas, a])
        f.decision, f.estado, f.reglas = "pagar", "pagada", [asdict(x) for x in d.reglas]
        partes = [f"Pagada con aprobación de {quienes}, que revisó: "
                  + "; ".join(f"{motor.CATALOGO[r]['falla'].lower()} ({r})" for r in revisadas) + "."]
        if corr:
            partes.append("Datos corregidos: " + ", ".join(f"{k} = {v}" for k, v in corr.items()) + ".")
        partes.append(f"Comentario: «{comentario.strip()[:200]}».")
        partes.append("Kauta volvió a verificar las reglas duras (saldo, duplicados, bloqueos y máximo por pago) y se cumplen.")
        if any(r == "R07" for r in revisadas) and ben:
            partes.append(f"Se paga a la cuenta registrada (···{ben.cuenta_ultimos4}); un cambio de cuenta solo se aplica con verificación independiente.")
        f.motivo = " ".join(partes)
        p = _pagar_o_escalar(bd, f, reglas, f"{u.nombre} ({u.cargo})", None)
        bd.commit()
        return {"ok": p is not None, "completa": True, "mensaje": f.motivo, "pago": p.id if p else None}


def rechazar(bd: Session, fid: str, u: Usuario, comentario: str) -> dict[str, Any]:
    with BLOQUEO:
        f = bd.get(Factura, fid)
        if not f or f.estado != "pendiente":
            raise ErrorNegocio("Solo se rechazan facturas pendientes.")
        if not (comentario or "").strip():
            raise ErrorNegocio("Escriba el motivo del rechazo.")
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        datos = pagos.datos_aprobacion(f, f.beneficiario_id, "", u.id, 0, "rechazar", ts)
        a = Aprobacion(factura_id=fid, usuario_id=u.id, usuario_nombre=u.nombre, nivel=0, accion="rechazar",
                       comentario=comentario.strip()[:1000], datos_firmados=datos, firma=firma.firmar(datos))
        bd.add(a)
        bd.flush()
        costos.registrar_revision(bd, f, a, u.correo)
        f.estado = "rechazada"
        f.motivo = f"Rechazada por {u.nombre}. Comentario: «{comentario.strip()[:200]}»."
        auditoria.registrar(bd, "rechazo", f"{u.nombre} ({u.cargo})", "factura", fid, f.motivo, {})
        bd.commit()
        return {"ok": True, "mensaje": f.motivo}


def reevaluar(bd: Session, actor: str, beneficiario_id: str | None = None, cambio_por: str | None = None) -> list[str]:
    """Con reglas o datos nuevos, vuelve a evaluar en orden las frenadas y pendientes (las pagadas no se tocan).

    Si la reevaluación la provoca una persona (`cambio_por`), Kauta nunca paga sola por ese cambio: lo que
    pasaría a «pagar» queda pendiente, ninguna pendiente necesita menos firmas que antes y quien hizo el
    cambio no puede ser la firma única (control contra subir el umbral y firmar uno mismo).
    """
    cambiadas = []
    with BLOQUEO:
        reglas = reglas_vigentes(bd)
        bens = beneficiarios_motor(bd)
        consulta = select(Factura).where(Factura.estado.in_(("frenada", "pendiente")))
        if beneficiario_id:
            consulta = consulta.where(Factura.beneficiario_id == beneficiario_id)
        for f in bd.execute(consulta.order_by(Factura.recibida_en, Factura.id)).scalars().all():
            antes = f.estado
            d = motor.evaluar({"factura_id": f.id, "extraccion": f.extraccion, "hashes": f.hashes}, reglas, bens,
                              historial(bd, excluir=f.id))
            nuevo = ESTADO[d.decision]
            f.reglas, f.version_reglas, f.decision, f.motivo = [asdict(x) for x in d.reglas], reglas["version"], d.decision, d.motivo
            umbral = Decimal(str(reglas["umbral_aprobacion_usd"]))
            antes_requeridas = f.aprobaciones_requeridas if antes == "pendiente" else 0
            f.aprobaciones_requeridas = 0 if d.decision != "escalar" else (2 if Decimal(str(d.monto_usd or 0)) > umbral else 1)
            if cambio_por and nuevo in ("pagada", "pendiente"):
                if nuevo == "pagada":
                    nuevo, f.decision = "pendiente", "escalar"
                    f.motivo = (f"Escalada · Cambio de reglas: con las reglas v{reglas['version']} la factura cumple, pero Kauta "
                                "no paga sola después de un cambio; falta la firma de una persona distinta de quien lo hizo.")
                f.aprobaciones_requeridas = max(f.aprobaciones_requeridas, antes_requeridas, 1)
                f.excluir_firmante = cambio_por
            f.estado = nuevo
            bd.flush()
            if nuevo != antes:
                if nuevo == "pagada":
                    _pagar_o_escalar(bd, f, reglas, actor, None)
                cambiadas.append(f.id)
                auditoria.registrar(bd, "reevaluacion", actor, "factura", f.id,
                                    f"Con las reglas v{reglas['version']}: {antes} → {f.estado}. {f.motivo[:200]}", {})
        bd.commit()
    return cambiadas


# ---------------------------------------------------------------------------
# Métricas para el jurado
# ---------------------------------------------------------------------------
def regla_principal(motivo: str) -> str:
    m = re.search(r"\((R\d{2})\)", motivo or "")
    return m.group(1) if m and not motivo.startswith("Pagada") else "—"


def metricas(bd: Session) -> dict[str, Any]:
    """Las métricas viven en servicios/metricas.py (una sola fuente para Resumen, Recibo y Rendimiento)."""
    from . import metricas as m
    return m.base(bd)
