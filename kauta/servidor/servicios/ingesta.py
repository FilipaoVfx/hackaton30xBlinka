"""Escucha Gmail por consulta periódica, con recepción durable e importación idempotente.

Una factura y su enlace al correo se confirman en la misma transacción. Un reinicio
no repite decisiones. La deduplicación financiera sigue siendo responsabilidad del motor.
"""
from __future__ import annotations

import asyncio
import fcntl
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path

from sqlalchemy import func, select

from ..config import CONFIG, VAR
from ..db import SesionBD
from ..ingesta_modelos import CorreoRecibido, DocumentoRecibido, FuenteCorreo
from ..modelos import Factura, ahora
from . import BLOQUEO, agente, auditoria
from .gmail import ConfigGmail, ErrorGmail, Gmail

LOG = logging.getLogger(__name__)
CONFIG_GMAIL = ConfigGmail.cargar()
CLIENTE = Gmail(CONFIG_GMAIL)
EXTENSIONES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".xml", ".zip", ".txt", ".eml"}


def iso(t):
    return t.replace(tzinfo=timezone.utc).isoformat() if t else None


def fuente(bd, config=CONFIG_GMAIL):
    f = bd.get(FuenteCorreo, config.cuenta)
    if not f:
        desde = datetime.fromisoformat(config.desde.replace("Z", "+00:00")) if config.desde else ahora()
        if desde.tzinfo:
            desde = desde.astimezone(timezone.utc).replace(tzinfo=None)
        f = FuenteCorreo(cuenta=config.cuenta, desde=desde)
        bd.add(f)
        bd.commit()
    return f


def estado(bd, config=CONFIG_GMAIL):
    f = bd.get(FuenteCorreo, config.cuenta)
    credencial = config.credenciales.is_file()
    if not config.activo:
        e = "desactivada"
    elif not credencial:
        e = "requiere_autorizacion"
    elif f and f.error:
        e = "error"
    elif f and f.ultimo_exito and (ahora() - f.ultimo_exito).total_seconds() <= config.intervalo * 3:
        e = "escuchando"
    else:
        e = "sin_senal"
    consulta = select(DocumentoRecibido.estado, func.count()).join(CorreoRecibido).where(
        CorreoRecibido.cuenta == config.cuenta, DocumentoRecibido.estado != "eliminado").group_by(DocumentoRecibido.estado)
    conteos = dict(bd.execute(consulta).all())
    return {"estado": e, "cuenta": config.cuenta, "asunto": config.asunto,
            "intervalo_segundos": config.intervalo, "desde": iso(f.desde) if f else None,
            "ultima_consulta": iso(f.ultima_consulta) if f else None,
            "ultimo_exito": iso(f.ultimo_exito) if f else None, "error": f.error if f else None,
            "documentos": conteos, "solo_lectura": True}


def documentos(bd, cuenta=CONFIG_GMAIL.cuenta):
    filas = bd.execute(select(DocumentoRecibido, CorreoRecibido).join(CorreoRecibido).where(
        CorreoRecibido.cuenta == cuenta, DocumentoRecibido.estado != "eliminado").order_by(DocumentoRecibido.id.desc()).limit(100)).all()
    return [{"id": d.id, "nombre": d.nombre, "estado": d.estado, "motivo": d.motivo,
             "factura_id": d.factura_id, "intentos": d.intentos, "asunto": c.asunto,
             "remitente": c.remitente, "recibida_en": iso(c.recibida_en)} for d, c in filas]


def _guardar(carpeta: str, datos: bytes, extension: str):
    destino = VAR / "correo" / carpeta
    destino.mkdir(parents=True, exist_ok=True, mode=0o700)
    h = hashlib.sha256(datos).hexdigest()
    ruta = destino / (h + extension)
    if not ruta.exists():
        # Nunca se usan nombres del remitente para formar una ruta.
        with ruta.open("wb") as archivo:
            archivo.write(datos)
        ruta.chmod(0o600)
    return str(ruta), h


def recibir(bd, meta, raw: bytes, config=CONFIG_GMAIL):
    """Preserva el MIME completo; PDF/XML del mismo nombre constituyen un solo documento."""
    previo = bd.scalar(select(CorreoRecibido).where(CorreoRecibido.cuenta == config.cuenta,
                                                   CorreoRecibido.mensaje_id == meta["id"]))
    if previo:
        return previo
    if len(raw) > config.max_mensaje_mb * 1024 * 1024:
        raise ErrorGmail("El correo supera el límite de recepción.")
    mensaje = BytesParser(policy=policy.default).parsebytes(raw)
    if not re.search(r"(?<!\w)" + re.escape(config.asunto) + r"(?!\w)", str(mensaje.get("Subject", "")), re.I):
        return None
    if "INBOX" not in meta.get("labelIds", []):
        return None
    ruta, _ = _guardar("originales", raw, ".eml")
    c = CorreoRecibido(cuenta=config.cuenta, mensaje_id=meta["id"], hilo_id=meta.get("threadId", ""),
                       asunto=str(mensaje.get("Subject", ""))[:500], remitente=str(mensaje.get("From", ""))[:500],
                       recibida_en=datetime.fromtimestamp(int(meta["internalDate"]) / 1000, timezone.utc).replace(tzinfo=None),
                       ruta_original=ruta)
    bd.add(c)
    bd.flush()
    partes = []
    for indice, p in enumerate(mensaje.walk()):
        nombre = p.get_filename()
        if p.is_multipart() or not nombre or p.get_content_disposition() == "inline":
            continue
        nombre = re.sub(r"[^\w.\- ]", "_", nombre.replace("\\", "/").split("/")[-1])[:180] or "adjunto"
        datos = p.get_payload(decode=True) or b""
        partes.append((str(indice), nombre, datos))
    if not partes:
        # Un correo sin adjuntos puede contener una cuenta de cobro en su cuerpo.
        partes = [("cuerpo", "cuenta-de-cobro.eml", raw)]
    canonicos = {Path(n).stem.casefold(): i for i, n, _ in partes if Path(n).suffix.lower() == ".xml"}
    for parte, nombre, datos in partes:
        ext = Path(nombre).suffix.lower()
        motivo, est = "En cola de lectura.", "recibido"
        if ext not in EXTENSIONES:
            est, motivo = "revision", "Formato no compatible. El adjunto permanece en el correo original."
        elif len(datos) > CONFIG.max_archivo_mb * 1024 * 1024:
            est, motivo = "revision", f"El documento supera {CONFIG.max_archivo_mb} MB. Requiere revisión."
        elif not datos:
            est, motivo = "revision", "El adjunto está vacío."
        elif ext == ".pdf" and Path(nombre).stem.casefold() in canonicos:
            est, motivo = "soporte", "PDF conservado como soporte; se procesa el XML fiscal con el mismo nombre."
        ruta_doc, huella = _guardar("documentos", datos, ext if ext in EXTENSIONES else ".bin")
        bd.add(DocumentoRecibido(correo_id=c.id, parte=parte, nombre=nombre, huella=huella,
                                ruta=ruta_doc, estado=est, motivo=motivo))
    auditoria.registrar(bd, "correo.recibido", "Recolector Gmail", "correo", str(c.id),
                        f"Correo recibido con {len(partes)} documento(s).", {"mensaje_id": c.mensaje_id})
    bd.commit()
    return c


def procesar_documento(bd, documento_id: int, *, reintentar=False):
    with BLOQUEO:
        d = bd.get(DocumentoRecibido, documento_id, populate_existing=True)
        if not d or (d.estado != "recibido" and not (reintentar and d.estado == "error_lectura")):
            return
        # La huella identifica documentos idénticos incluso si llegan en otro correo o canal.
        existente = bd.scalar(select(Factura).where(Factura.hash_documento == d.huella).limit(1))
        if existente:
            d.estado, d.factura_id = "duplicado", existente.id
            d.motivo = f"Documento ya registrado como {existente.id}. No se repite la decisión."
        else:
            d.intentos += 1
            try:
                datos = Path(d.ruta).read_bytes()
                # Un nombre F01_... enviado por correo jamás habilita la extracción ficticia del set.
                nombre_lector = f"gmail_{d.huella[:12]}_{d.nombre}"
                from ..rutas.negocio import _tipo_real
                _tipo_real(d.nombre, datos)
                resultado = agente.EXTRACTOR.extraer(nombre_lector, datos)
                c = bd.get(CorreoRecibido, d.correo_id)
                with bd.begin_nested():
                    f = agente.registrar(bd, d.nombre, resultado, "gmail", "Recolector Gmail", parseaddr(c.remitente)[1].lower(),
                                         ruta=d.ruta, confirmar=False)
                    d.estado, d.factura_id = "procesado", f.id
                    d.motivo = f"{f.decision.capitalize()}: {f.motivo}"
                    auditoria.registrar(bd, "correo.documento_procesado", "Recolector Gmail", "factura", f.id,
                                        "Factura registrada desde Gmail con las reglas vigentes.",
                                        {"correo_id": c.id, "documento_id": d.id, "huella": d.huella})
                    bd.flush()
            except Exception as e:
                # No se exponen excepciones de SDKs (pueden incluir cuerpos, rutas o credenciales).
                from fastapi import HTTPException
                d.estado = "error_lectura"
                d.motivo = (str(e) if isinstance(e, agente.ErrorNegocio) else str(e.detail)
                            if isinstance(e, HTTPException) else "No se pudo leer el documento. Requiere revisión o reintento.")[:800]
                auditoria.registrar(bd, "correo.error_lectura", "Recolector Gmail", "correo", str(d.correo_id),
                                    d.motivo, {"documento_id": d.id})
        bd.commit()


def eliminar_documento(bd, documento_id: int, actor: str):
    """Borrado lógico de recepción: conserva el ID de Gmail y la evidencia financiera."""
    with BLOQUEO:
        d = bd.get(DocumentoRecibido, documento_id, populate_existing=True)
        if not d:
            return None
        correo = bd.get(CorreoRecibido, d.correo_id)
        if correo.cuenta != CONFIG_GMAIL.cuenta:
            return None
        if d.estado != "eliminado":
            anterior = d.estado
            d.estado = "eliminado"
            auditoria.registrar(bd, "correo.documento_eliminado", actor, "correo", str(d.correo_id),
                                "Documento eliminado de la recepción de correo.",
                                {"documento_id": d.id, "nombre": d.nombre, "estado_anterior": anterior,
                                 "factura_id": d.factura_id, "huella": d.huella})
            bd.commit()
        return d


def ejecutar(config=CONFIG_GMAIL, cliente=None):
    """Un ciclo. La exclusión de proceso impide duplicar el trabajo con varios workers."""
    if not config.activo:
        return
    VAR.mkdir(parents=True, exist_ok=True)
    with (VAR / "gmail.lock").open("a") as candado:
        try:
            fcntl.flock(candado, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        with SesionBD() as bd:
            f = fuente(bd, config)
            inicio = ahora()
            f.ultima_consulta = inicio
            bd.commit()
            try:
                cliente = cliente or CLIENTE
                cliente.perfil()  # valida siempre la cuenta antes de importar
                base = max(f.desde, (f.cursor - timedelta(days=2)) if f.cursor else f.desde)
                consulta = f"in:inbox subject:{config.asunto} after:{int(base.replace(tzinfo=timezone.utc).timestamp())}"
                pagina = ""
                while True:
                    lote = cliente.listar(consulta, pagina)
                    for m in lote.get("messages", []):
                        if bd.scalar(select(CorreoRecibido.id).where(CorreoRecibido.cuenta == config.cuenta,
                                                                   CorreoRecibido.mensaje_id == m["id"])):
                            continue
                        meta = cliente.metadatos(m["id"])
                        fecha = datetime.fromtimestamp(int(meta["internalDate"]) / 1000, timezone.utc).replace(tzinfo=None)
                        if fecha < f.desde:
                            continue
                        if meta.get("sizeEstimate", 0) > config.max_mensaje_mb * 1024 * 1024:
                            headers = {h["name"].lower(): h["value"] for h in meta.get("payload", {}).get("headers", [])}
                            c = CorreoRecibido(cuenta=config.cuenta, mensaje_id=m["id"], hilo_id=meta.get("threadId", ""),
                                               asunto=headers.get("subject", "")[:500], remitente=headers.get("from", "")[:500],
                                               recibida_en=fecha, error="El correo supera el límite de recepción.")
                            bd.add(c)
                            bd.flush()
                            bd.add(DocumentoRecibido(correo_id=c.id, parte="limite", nombre="Correo demasiado grande",
                                                    huella="", estado="revision", motivo=c.error))
                            bd.commit()
                        else:
                            with BLOQUEO:
                                recibir(bd, meta, cliente.original(m["id"]), config)
                    pagina = lote.get("nextPageToken", "")
                    if not pagina:
                        break
                # Incluye documentos guardados antes de un reinicio; no reintenta automáticamente la IA.
                pendientes = bd.scalars(select(DocumentoRecibido.id).join(CorreoRecibido).where(
                    CorreoRecibido.cuenta == config.cuenta, DocumentoRecibido.estado == "recibido")).all()
                for did in pendientes:
                    procesar_documento(bd, did)
                f.cursor, f.ultimo_exito, f.error = inicio, ahora(), None
                bd.commit()
            except Exception as e:
                bd.rollback()
                f = fuente(bd, config)
                f.error = str(e) if isinstance(e, ErrorGmail) else "La sincronización se interrumpió. Se reintentará sin duplicar documentos."
                bd.commit()
                LOG.warning("Consulta Gmail interrumpida: %s", type(e).__name__)


async def escuchar(detener: asyncio.Event):
    while not detener.is_set():
        try:
            await asyncio.to_thread(ejecutar)
        except Exception:
            LOG.exception("No se pudo ejecutar el ciclo de recepción Gmail")
        try:
            await asyncio.wait_for(detener.wait(), timeout=CONFIG_GMAIL.intervalo)
        except asyncio.TimeoutError:
            pass
