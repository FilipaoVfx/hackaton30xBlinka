"""Facturas, aprobaciones (Kauta pregunta), proveedores, cambios de cuenta y reglas."""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select

from ..config import CONFIG, RAIZ, VAR
from ..esquemas import AprobarIn, RechazarIn, ReglasIn, VerificarCambioIn
from ..modelos import Beneficiario, CambioCuenta, Factura, VersionReglas, ahora
from ..seguridad import totp
from ..seguridad.cifrado import cifrar, descifrar
from ..seguridad.limites import limitar
from ..seguridad.sesiones import Contexto, requiere
from ..servicios import BLOQUEO, agente, auditoria, wallet
from ..servicios.agente import ErrorNegocio
from .. import vistas

r = APIRouter(prefix="/api", tags=["Negocio"])
FIRMAS = {b"%PDF-": ".pdf", b"\x89PNG": ".png", b"\xff\xd8\xff": ".jpg", b"PK\x03\x04": ".zip"}
PERMITIDAS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".eml", ".txt", ".xml", ".zip"}


def _tipo_real(nombre: str, datos: bytes) -> str:
    """Valida por contenido (bytes mágicos), no solo por la extensión que dice el archivo."""
    ext = Path(nombre).suffix.lower()
    if ext not in PERMITIDAS:
        raise HTTPException(415, f"Tipo de archivo no permitido ({ext or 'sin extensión'}).")
    for firma, e in FIRMAS.items():
        if datos.startswith(firma):
            if e != ext and not (e == ".jpg" and ext == ".jpeg"):
                raise HTTPException(415, f"El contenido es {e} pero el nombre dice {ext}: archivo sospechoso.")
            return e
    if ext == ".webp" and datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return ext
    if ext in (".eml", ".txt", ".xml"):
        try:
            datos[:65536].decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(415, "El archivo de texto no es UTF-8 válido.")
        return ext
    raise HTTPException(415, "El contenido del archivo no coincide con su tipo.")


@r.get("/facturas")
def listar(estado: str | None = None, q: str | None = None, ctx: Contexto = Depends(requiere("ver"))):
    consulta = select(Factura).order_by(Factura.recibida_en.desc(), Factura.id.desc())
    if estado:
        consulta = consulta.where(Factura.estado == estado)
    filas = ctx.bd.execute(consulta).scalars().all()
    if q:
        t = q.lower()[:60]
        filas = [f for f in filas if t in f"{f.id} {f.beneficiario_nombre} {f.numero} {f.archivo}".lower()]
    return [vistas.factura_resumen(ctx.bd, f) for f in filas]


@r.get("/facturas/{fid}")
def detalle(fid: str, ctx: Contexto = Depends(requiere("ver"))):
    f = ctx.bd.get(Factura, fid)
    if not f:
        raise HTTPException(404, "Factura no encontrada.")
    return vistas.factura_detalle(ctx.bd, f)


@r.get("/facturas/{fid}/vista")
def vista(fid: str, ctx: Contexto = Depends(requiere("ver"))):
    """Vista previa como PNG re-codificado (nunca se entrega el archivo original al navegador)."""
    f = ctx.bd.get(Factura, fid)
    if not f:
        raise HTTPException(404)
    previa = RAIZ / "data" / "previews" / f"{f.id}.png"
    if f.origen == "set" and previa.exists():
        return FileResponse(previa, media_type="image/png", headers={"Content-Disposition": "inline"})
    cache = VAR / "vistas" / f"{f.hash_documento}.png"
    if not cache.exists() and f.ruta_archivo:
        cache.parent.mkdir(parents=True, exist_ok=True)
        datos = Path(f.ruta_archivo).read_bytes()
        try:
            from PIL import Image
            if datos.startswith(b"%PDF-"):
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(datos)
                img = doc[0].render(scale=1.3).to_pil()
                doc.close()
            elif f.canal == "imagen":
                img = Image.open(io.BytesIO(datos))
                img.thumbnail((1400, 1400))
            elif f.canal == "correo":
                from kauta.extractor import leer_documento
                d = leer_documento(f.archivo, datos)
                if d["pdfs"]:
                    import pypdfium2 as pdfium
                    doc = pdfium.PdfDocument(d["pdfs"][0])
                    img = doc[0].render(scale=1.3).to_pil()
                    doc.close()
                elif d["imagenes"]:
                    img = Image.open(io.BytesIO(d["imagenes"][0][1]))
                else:
                    raise HTTPException(404)
            else:
                raise HTTPException(404)
            img.convert("RGB").save(cache, "PNG")  # re-codificar elimina metadatos y contenido incrustado
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(404, "No hay vista previa para este documento.")
    if not cache.exists():
        raise HTTPException(404)
    return FileResponse(cache, media_type="image/png", headers={"Content-Disposition": "inline"})


@r.post("/facturas/cargar")
async def cargar(archivo: UploadFile = File(...), ctx: Contexto = Depends(requiere("facturas.cargar"))):
    limitar(f"carga:{ctx.usuario.id}", 30, 60)
    tope = CONFIG.max_archivo_mb * 1024 * 1024
    datos = await archivo.read(tope + 1)
    if len(datos) > tope:
        raise HTTPException(413, f"El archivo supera {CONFIG.max_archivo_mb} MB.")
    nombre = re.sub(r"[^\w.\-]", "_", Path(archivo.filename or "documento").name)[:100]
    _tipo_real(nombre, datos)
    try:
        f = agente.procesar_archivo(ctx.bd, nombre, datos, "carga", ctx.actor, ctx.usuario.correo)
    except ErrorNegocio as e:
        raise HTTPException(422, str(e))
    return vistas.factura_detalle(ctx.bd, f)


@r.post("/facturas/sorpresa")
def sorpresa(ctx: Contexto = Depends(requiere("facturas.cargar"))):
    """Procesa los archivos de data/sorpresa (XML fiscal, contenedor DIAN, un XML malicioso y una nota crédito)."""
    hechas = []
    for p in sorted((RAIZ / "data" / "sorpresa").glob("S0*")):
        if ctx.bd.get(Factura, p.name[:3]):
            continue
        f = agente.procesar_archivo(ctx.bd, p.name, p.read_bytes(), "sorpresa", ctx.actor, ctx.usuario.correo)
        hechas.append(vistas.factura_resumen(ctx.bd, f))
    return hechas


@r.post("/facturas/{fid}/aprobar")
def aprobar(fid: str, datos: AprobarIn, ctx: Contexto = Depends(requiere("facturas.aprobar"))):
    u = ctx.usuario
    con_mfa = False
    if u.mfa_activo:
        paso = totp.verificar_codigo(u.totp_cifrado, u.id, datos.codigo_totp or "", u.totp_ultimo_paso)
        if paso is None:
            raise HTTPException(401, "Para aprobar pagos se pide de nuevo su código de verificación (step-up).")
        u.totp_ultimo_paso, con_mfa = paso, True
    elif not CONFIG.demo:
        raise HTTPException(403, "En producción, aprobar pagos exige el segundo factor activo.")
    correcciones = datos.correcciones.model_dump(exclude_none=True) if datos.correcciones else None
    try:
        return agente.aprobar(ctx.bd, fid, u, datos.comentario, correcciones, con_mfa)
    except ErrorNegocio as e:
        raise HTTPException(409, str(e))


@r.post("/facturas/{fid}/rechazar")
def rechazar(fid: str, datos: RechazarIn, ctx: Contexto = Depends(requiere("facturas.aprobar"))):
    try:
        return agente.rechazar(ctx.bd, fid, ctx.usuario, datos.comentario)
    except ErrorNegocio as e:
        raise HTTPException(409, str(e))


@r.get("/aprobaciones")
def bandeja_aprobaciones(ctx: Contexto = Depends(requiere("ver"))):
    pendientes = ctx.bd.execute(select(Factura).where(Factura.estado == "pendiente")
                                .order_by(Factura.recibida_en)).scalars().all()
    salida = []
    for f in pendientes:
        d = vistas.factura_resumen(ctx.bd, f)
        d["preguntas"] = vistas.preguntas(ctx.bd, f)
        d["plazo"] = vistas.plazo(ctx.bd, f)
        d["ya_aprobe"] = any(a.usuario_id == ctx.usuario.id for a in f.aprobaciones)
        d["cargue_yo"] = f.cargada_por == ctx.usuario.correo
        d["aprobadores"] = [a.usuario_nombre for a in f.aprobaciones if a.accion == "aprobar"]
        salida.append(d)
    return salida


# ----------------------------------------------------------------- proveedores
@r.get("/proveedores")
def proveedores(ctx: Contexto = Depends(requiere("ver"))):
    return [vistas.beneficiario_dict(ctx.bd, b) for b in ctx.bd.execute(select(Beneficiario).order_by(Beneficiario.id)).scalars()]


@r.get("/cambios-cuenta")
def cambios(ctx: Contexto = Depends(requiere("ver"))):
    filas = ctx.bd.execute(select(CambioCuenta).order_by(CambioCuenta.creada_en.desc())).scalars().all()
    return [vistas.cambio_dict(ctx.bd, c) for c in filas]


@r.post("/cambios-cuenta/{cid}/verificar")
def verificar_cambio(cid: int, datos: VerificarCambioIn, ctx: Contexto = Depends(requiere("cuentas.verificar"))):
    with BLOQUEO:
        c = ctx.bd.get(CambioCuenta, cid)
        if not c or c.estado != "pendiente":
            raise HTTPException(409, "La solicitud no existe o ya se resolvió.")
        if c.solicitada_por == ctx.usuario.correo:
            raise HTTPException(409, "Segregación de funciones: quien pide el cambio no puede verificarlo.")
        b = ctx.bd.get(Beneficiario, c.beneficiario_id)
        c.verificada_por, c.metodo_verificacion, c.resuelta_en = ctx.actor, datos.metodo, ahora()
        if datos.aprobar:
            anterior = b.cuenta_ultimos4
            nueva = descifrar(c.cuenta_nueva_cifrada, aad=f"cambio:{b.id}")
            b.cuenta_cifrada = cifrar(f"Cuenta {nueva} · {c.banco_nuevo}", aad=f"cuenta:{b.id}")
            b.cuenta_ultimos4, b.banco = c.ultimos4_nuevos, f"{c.banco_nuevo} · verificada por llamada"
            b.verificada_por, b.verificada_en = f"{ctx.actor} · {datos.metodo}", ahora()
            c.estado = "aprobado"
            resumen = f"Cuenta de {b.nombre} cambiada de ···{anterior} a ···{c.ultimos4_nuevos} tras verificación: {datos.metodo}."
        else:
            c.estado = "rechazado"
            resumen = f"Cambio de cuenta de {b.nombre} rechazado ({datos.metodo}). {datos.comentario}".strip()
        auditoria.registrar(ctx.bd, "cuenta.cambio_" + c.estado, ctx.actor, "beneficiario", b.id, resumen,
                            {"solicitud": c.id, "comentario": datos.comentario})
        ctx.bd.commit()
    cambiadas = agente.reevaluar(ctx.bd, ctx.actor, beneficiario_id=c.beneficiario_id, cambio_por=ctx.usuario.correo) if datos.aprobar else []
    return {"ok": True, "mensaje": resumen, "reevaluadas": cambiadas}


# ----------------------------------------------------------------- reglas
@r.get("/reglas")
def reglas(ctx: Contexto = Depends(requiere("ver"))):
    versiones = ctx.bd.execute(select(VersionReglas).order_by(VersionReglas.version.desc())).scalars().all()
    from kauta.motor import CATALOGO
    return {"vigente": {**versiones[0].parametros, "version": versiones[0].version},
            "catalogo": [{"id": k, **v} for k, v in CATALOGO.items()],
            "versiones": [{"version": v.version, "creada_por": v.creada_por, "creada_en": vistas.iso(v.creada_en),
                           "motivo": v.motivo, "cambios": v.cambios} for v in versiones]}


@r.put("/reglas")
def cambiar_reglas(datos: ReglasIn, ctx: Contexto = Depends(requiere("reglas.editar"))):
    with BLOQUEO:
        actual = agente.reglas_vigentes(ctx.bd)
        nuevos = datos.model_dump(exclude={"motivo"})
        cambios = {k: {"antes": actual.get(k), "despues": v} for k, v in nuevos.items() if actual.get(k) != v}
        if not cambios:
            raise HTTPException(409, "No hay cambios respecto a la versión vigente.")
        version = actual["version"] + 1
        parametros = {k: v for k, v in actual.items() if k != "version"} | nuevos
        ctx.bd.add(VersionReglas(version=version, parametros=parametros, creada_por=ctx.actor, motivo=datos.motivo, cambios=cambios))
        if "presupuesto_periodo_usd" in cambios:  # la sub-wallet se ajusta al nuevo presupuesto
            from decimal import Decimal
            delta = Decimal(str(nuevos["presupuesto_periodo_usd"])) - Decimal(str(actual["presupuesto_periodo_usd"]))
            desde, hacia = ("operativa", "cxp") if delta > 0 else ("cxp", "operativa")
            for per in wallet.periodos_fondeados(ctx.bd):
                if delta != 0:
                    wallet.transferir(ctx.bd, "fondeo", f"Ajuste de la sub-wallet de {per} por cambio de presupuesto (reglas v{version})",
                                      f"REGLAS-v{version}-{per}", per, desde, hacia, abs(delta))
        auditoria.registrar(ctx.bd, "reglas.cambio", ctx.actor, "reglas", str(version),
                            f"Reglas v{version}: " + "; ".join(f"{k}: {v['antes']} → {v['despues']}" for k, v in cambios.items())
                            + f". Motivo: {datos.motivo}", {"cambios": cambios})
        ctx.bd.commit()
    cambiadas = agente.reevaluar(ctx.bd, ctx.actor, cambio_por=ctx.usuario.correo)
    return {"version": version, "cambios": cambios, "reevaluadas": cambiadas}


@r.post("/reglas/simular")
def simular_reglas(datos: ReglasIn, ctx: Contexto = Depends(requiere("ver"))):
    """¿Qué pasaría si…? Evalúa las facturas abiertas con reglas hipotéticas, sin guardar nada."""
    from kauta import motor
    actual = agente.reglas_vigentes(ctx.bd)
    hipotesis = {**actual, **datos.model_dump(exclude={"motivo"}), "version": actual["version"] + 1}
    bens = agente.beneficiarios_motor(ctx.bd)
    salida = []
    for f in ctx.bd.execute(select(Factura).where(Factura.estado.in_(("frenada", "pendiente")))
                            .order_by(Factura.recibida_en)).scalars():
        d = motor.evaluar({"factura_id": f.id, "extraccion": f.extraccion, "hashes": f.hashes}, hipotesis, bens,
                          agente.historial(ctx.bd, excluir=f.id))
        salida.append({"id": f.id, "beneficiario": f.beneficiario_nombre, "antes": f.decision, "despues": d.decision,
                       "motivo": d.motivo})
    return salida
