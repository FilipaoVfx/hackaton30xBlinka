"""Estado de la fuente y revisión de recepción. Ninguna ruta acepta o devuelve tokens OAuth."""
from fastapi import APIRouter, Depends, HTTPException

from ..ingesta_modelos import DocumentoRecibido
from ..seguridad.sesiones import Contexto, requiere
from ..servicios import ingesta

r = APIRouter(prefix="/api/correo", tags=["Recepción de facturas"])


@r.get("/estado")
def estado(ctx: Contexto = Depends(requiere("ver"))):
    return ingesta.estado(ctx.bd)


@r.get("/documentos")
def documentos(ctx: Contexto = Depends(requiere("ver"))):
    return ingesta.documentos(ctx.bd)


@r.delete("/documentos/{did}")
def eliminar(did: int, ctx: Contexto = Depends(requiere("facturas.cargar"))):
    d = ingesta.eliminar_documento(ctx.bd, did, ctx.actor)
    if d is None:
        raise HTTPException(404, "Documento no encontrado.")
    return {"ok": True, "estado": d.estado, "factura_id": d.factura_id}


@r.post("/documentos/{did}/reintentar")
def reintentar(did: int, ctx: Contexto = Depends(requiere("facturas.cargar"))):
    d = ctx.bd.get(DocumentoRecibido, did)
    if not d:
        raise HTTPException(404, "Documento no encontrado.")
    if d.estado != "error_lectura":
        raise HTTPException(409, "Solo se reintentan documentos con error de lectura.")
    ingesta.procesar_documento(ctx.bd, did, reintentar=True)
    return {"ok": True, "estado": d.estado, "factura_id": d.factura_id}
