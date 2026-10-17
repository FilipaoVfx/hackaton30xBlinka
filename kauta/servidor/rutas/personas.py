"""Personas de la empresa: invitación, registro con código, roles y estado de cada cuenta."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import obtener_bd
from ..esquemas import ActivoIn, CambioContrasenaIn, InvitarIn, RegistroIn, RolIn
from ..seguridad.limites import limitar
from ..seguridad.sesiones import Contexto, contexto, ip_de, requiere
from ..servicios import usuarios
from ..servicios.usuarios import ErrorUsuarios

r = APIRouter(prefix="/api", tags=["Personas"])


def _error(e: ErrorUsuarios) -> HTTPException:
    return HTTPException(409, str(e))


@r.get("/personas")
def listar(ctx: Contexto = Depends(requiere("usuarios.ver"))):
    """Lista de personas, invitaciones y roles. La ve administración y auditoría."""
    return usuarios.listar(ctx.bd)


@r.post("/personas/invitar")
def invitar(datos: InvitarIn, ctx: Contexto = Depends(requiere("usuarios.gestionar"))):
    """Crea la invitación. El código se devuelve una sola vez: después solo queda su hash."""
    try:
        inv, codigo = usuarios.invitar(ctx.bd, datos.correo, datos.nombre, datos.cargo, datos.rol, ctx.actor)
    except ErrorUsuarios as e:
        raise _error(e)
    return {"invitacion": usuarios.invitacion_dict(inv), "codigo": codigo,
            "aviso": "Entregue este código por un canal distinto al correo de la invitación. No se vuelve a mostrar."}


@r.delete("/personas/invitaciones/{inv_id}")
def revocar(inv_id: int, ctx: Contexto = Depends(requiere("usuarios.gestionar"))):
    try:
        return usuarios.invitacion_dict(usuarios.revocar_invitacion(ctx.bd, inv_id, ctx.actor))
    except ErrorUsuarios as e:
        raise _error(e)


@r.post("/personas/registro")
def registro(datos: RegistroIn, request: Request, bd: Session = Depends(obtener_bd)):
    """Alta de la propia persona con el código de invitación. No necesita sesión; el rol ya viene dado."""
    ip = ip_de(request)
    limitar(f"registro-ip:{ip}", 8, 900)                 # contra el ensayo de códigos a ciegas
    limitar(f"registro-correo:{datos.correo.lower()}", 6, 900)
    try:
        u = usuarios.registrar(bd, datos.codigo, datos.correo, datos.contrasena, ip)
    except ErrorUsuarios as e:
        raise _error(e)
    return {"ok": True, "correo": u.correo, "nombre": u.nombre, "rol": u.rol,
            "mensaje": "Cuenta creada. Ya puede entrar con su correo y su contraseña."}


@r.put("/personas/{usuario_id}/rol")
def rol(usuario_id: int, datos: RolIn, ctx: Contexto = Depends(requiere("usuarios.gestionar"))):
    try:
        return usuarios.usuario_dict(ctx.bd, usuarios.cambiar_rol(ctx.bd, usuario_id, datos.rol, ctx.actor))
    except ErrorUsuarios as e:
        raise _error(e)


@r.put("/personas/{usuario_id}/activo")
def activo(usuario_id: int, datos: ActivoIn, ctx: Contexto = Depends(requiere("usuarios.gestionar"))):
    try:
        return usuarios.usuario_dict(ctx.bd, usuarios.activar(ctx.bd, usuario_id, datos.activo, ctx.actor))
    except ErrorUsuarios as e:
        raise _error(e)


@r.post("/personas/{usuario_id}/desbloquear")
def desbloquear(usuario_id: int, ctx: Contexto = Depends(requiere("usuarios.gestionar"))):
    try:
        return usuarios.usuario_dict(ctx.bd, usuarios.desbloquear(ctx.bd, usuario_id, ctx.actor))
    except ErrorUsuarios as e:
        raise _error(e)


@r.post("/personas/mi-contrasena")
def mi_contrasena(datos: CambioContrasenaIn, ctx: Contexto = Depends(contexto)):
    """Cada persona cambia su propia contraseña."""
    try:
        usuarios.cambiar_contrasena(ctx.bd, ctx.usuario, datos.actual, datos.nueva)
    except ErrorUsuarios as e:
        raise _error(e)
    return {"ok": True, "mensaje": "Contraseña actualizada."}
