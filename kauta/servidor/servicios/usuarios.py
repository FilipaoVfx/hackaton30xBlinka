"""
Alta y gestión de personas: invitación, registro, cambio de rol y desactivación.

Cómo funciona el alta en una empresa (y por qué no es registro abierto):

  1. Alguien de **administración** invita a la persona: define su correo, su nombre, su cargo y el
     **rol** con el que entrará. El sistema genera un código de un solo uso.
  2. La persona abre «Crear cuenta», escribe ese código y elige su contraseña. El rol no lo elige
     ella: viene en la invitación.
  3. La invitación queda usada y no sirve de nuevo. Caduca a los 7 días.

Del código solo se guarda su hash Argon2id, igual que de una contraseña: si alguien se lleva la base
de datos, no puede usar las invitaciones pendientes. Todo queda en el registro de auditoría.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..modelos import Aprobacion, Factura, Invitacion, Sesion, Usuario
from ..seguridad import contrasenas
from ..seguridad.permisos import ROL_ADMIN, ROLES, etiqueta
from . import BLOQUEO, auditoria

DIAS_INVITACION = 7
MAX_INTENTOS_CODIGO = 8
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin letras ni dígitos que se confundan al dictarlos


class ErrorUsuarios(Exception):
    pass


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(f: datetime | None) -> datetime | None:
    return f if f is None or f.tzinfo else f.replace(tzinfo=timezone.utc)


def generar_codigo() -> str:
    """Código de 12 caracteres, en tres grupos, fácil de dictar por teléfono: KAU7-3BQX-9MFD."""
    cuerpo = "".join(secrets.choice(ALFABETO) for _ in range(8))
    return f"KAU{secrets.choice(ALFABETO)}-{cuerpo[:4]}-{cuerpo[4:]}"


def normalizar_correo(correo: str) -> str:
    return (correo or "").strip().lower()


# ---------------------------------------------------------------------------
# Invitaciones
# ---------------------------------------------------------------------------
def invitar(bd: Session, correo: str, nombre: str, cargo: str, rol: str, actor: str) -> tuple[Invitacion, str]:
    """Crea la invitación y devuelve el código en claro: se muestra una sola vez."""
    correo = normalizar_correo(correo)
    if rol not in ROLES:
        raise ErrorUsuarios(f"El rol «{rol}» no existe.")
    if not correo or "@" not in correo:
        raise ErrorUsuarios("Escriba un correo válido.")
    if not (nombre or "").strip():
        raise ErrorUsuarios("Escriba el nombre de la persona.")
    with BLOQUEO:
        if bd.execute(select(Usuario).where(func.lower(Usuario.correo) == correo)).scalar_one_or_none():
            raise ErrorUsuarios("Ya existe una cuenta con ese correo.")
        abierta = bd.execute(select(Invitacion).where(Invitacion.correo == correo, Invitacion.usada_en.is_(None),
                                                      Invitacion.revocada.is_(False))).scalars().all()
        for i in abierta:                       # una invitación nueva reemplaza a la anterior
            i.revocada = True
        codigo = generar_codigo()
        inv = Invitacion(correo=correo, nombre=nombre.strip(), cargo=(cargo or "").strip() or "Sin cargo", rol=rol,
                         hash_codigo=contrasenas.hashear(codigo), prefijo=codigo[:4], creada_por=actor,
                         expira_en=ahora() + timedelta(days=DIAS_INVITACION))
        bd.add(inv)
        bd.flush()
        auditoria.registrar(bd, "usuario.invitado", actor, "usuario", correo,
                            f"Invitación para {nombre} ({correo}) con el rol {ROLES[rol]['nombre']}.",
                            {"rol": rol, "prefijo": inv.prefijo, "expira_en": inv.expira_en.isoformat()})
        bd.commit()
    return inv, codigo


def revocar_invitacion(bd: Session, inv_id: int, actor: str) -> Invitacion:
    with BLOQUEO:
        inv = bd.get(Invitacion, inv_id)
        if not inv:
            raise ErrorUsuarios("La invitación no existe.")
        if inv.usada_en:
            raise ErrorUsuarios("Esa invitación ya se usó.")
        inv.revocada = True
        auditoria.registrar(bd, "usuario.invitacion_revocada", actor, "usuario", inv.correo,
                            f"Invitación de {inv.correo} revocada.", {"prefijo": inv.prefijo})
        bd.commit()
    return inv


def registrar(bd: Session, codigo: str, correo: str, contrasena: str, ip: str | None = None) -> Usuario:
    """Crea la cuenta a partir de una invitación. La persona elige su contraseña; el rol ya viene dado."""
    correo = normalizar_correo(correo)
    codigo = (codigo or "").strip().upper()
    with BLOQUEO:
        inv = bd.execute(select(Invitacion).where(Invitacion.correo == correo, Invitacion.usada_en.is_(None),
                                                  Invitacion.revocada.is_(False))
                         .order_by(Invitacion.id.desc())).scalars().first()
        generico = "La invitación no es válida, ya se usó o está vencida."
        if not inv:
            raise ErrorUsuarios(generico)
        if _aware(inv.expira_en) < ahora():
            raise ErrorUsuarios(generico)
        if inv.intentos >= MAX_INTENTOS_CODIGO:
            inv.revocada = True
            bd.commit()
            raise ErrorUsuarios("Demasiados intentos con el código: la invitación quedó bloqueada. Pida una nueva.")
        if not contrasenas.verificar(inv.hash_codigo, codigo):
            inv.intentos += 1
            auditoria.registrar(bd, "usuario.codigo_incorrecto", correo, "usuario", correo,
                                f"Código de invitación incorrecto para {correo} (intento {inv.intentos}).", {"ip": ip})
            bd.commit()
            raise ErrorUsuarios(generico)
        problemas = contrasenas.problemas_politica(contrasena, correo)
        if problemas:
            raise ErrorUsuarios(" ".join(problemas))
        if bd.execute(select(Usuario).where(func.lower(Usuario.correo) == correo)).scalar_one_or_none():
            raise ErrorUsuarios("Ya existe una cuenta con ese correo.")
        u = Usuario(correo=correo, nombre=inv.nombre, cargo=inv.cargo, rol=inv.rol,
                    hash_contrasena=contrasenas.hashear(contrasena))
        bd.add(u)
        inv.usada_en = ahora()
        bd.flush()
        auditoria.registrar(bd, "usuario.creado", correo, "usuario", correo,
                            f"{u.nombre} creó su cuenta con el rol {ROLES[u.rol]['nombre']} usando la invitación "
                            f"{inv.prefijo}…", {"rol": u.rol, "ip": ip})
        bd.commit()
    return u


# ---------------------------------------------------------------------------
# Gestión
# ---------------------------------------------------------------------------
def cambiar_rol(bd: Session, usuario_id: int, rol: str, actor: str) -> Usuario:
    if rol not in ROLES:
        raise ErrorUsuarios(f"El rol «{rol}» no existe.")
    with BLOQUEO:
        u = bd.get(Usuario, usuario_id)
        if not u:
            raise ErrorUsuarios("La persona no existe.")
        if u.rol == rol:
            return u
        if u.rol == ROL_ADMIN and rol != ROL_ADMIN and _admins(bd) <= 1:
            raise ErrorUsuarios("Debe quedar al menos una persona en administración.")
        antes, u.rol = u.rol, rol
        auditoria.registrar(bd, "usuario.rol_cambiado", actor, "usuario", u.correo,
                            f"{u.nombre}: rol {ROLES[antes]['nombre']} → {ROLES[rol]['nombre']}.",
                            {"antes": antes, "despues": rol})
        bd.commit()
    return u


def activar(bd: Session, usuario_id: int, activo: bool, actor: str) -> Usuario:
    """Desactivar cierra además todas sus sesiones: el acceso se corta de inmediato."""
    with BLOQUEO:
        u = bd.get(Usuario, usuario_id)
        if not u:
            raise ErrorUsuarios("La persona no existe.")
        if not activo and u.rol == ROL_ADMIN and _admins(bd) <= 1:
            raise ErrorUsuarios("Debe quedar al menos una persona en administración.")
        u.activo = activo
        if not activo:
            u.bloqueado_hasta = None
            u.intentos_fallidos = 0
            for s in bd.execute(select(Sesion).where(Sesion.usuario_id == u.id, Sesion.revocada.is_(False))).scalars():
                s.revocada = True
        auditoria.registrar(bd, "usuario.activo" if activo else "usuario.desactivado", actor, "usuario", u.correo,
                            f"{u.nombre} quedó {'activa' if activo else 'desactivada'}.", {"rol": u.rol})
        bd.commit()
    return u


def desbloquear(bd: Session, usuario_id: int, actor: str) -> Usuario:
    with BLOQUEO:
        u = bd.get(Usuario, usuario_id)
        if not u:
            raise ErrorUsuarios("La persona no existe.")
        u.intentos_fallidos, u.bloqueado_hasta = 0, None
        auditoria.registrar(bd, "usuario.desbloqueado", actor, "usuario", u.correo,
                            f"{u.nombre} quedó desbloqueada tras intentos fallidos.", {})
        bd.commit()
    return u


def cambiar_contrasena(bd: Session, u: Usuario, actual: str, nueva: str) -> Usuario:
    """La propia persona cambia su contraseña; se cierran las demás sesiones."""
    if not contrasenas.verificar(u.hash_contrasena, actual):
        raise ErrorUsuarios("La contraseña actual no coincide.")
    problemas = contrasenas.problemas_politica(nueva, u.correo)
    if problemas:
        raise ErrorUsuarios(" ".join(problemas))
    with BLOQUEO:
        u.hash_contrasena = contrasenas.hashear(nueva)
        auditoria.registrar(bd, "usuario.contrasena_cambiada", f"{u.nombre} ({u.cargo})", "usuario", u.correo,
                            f"{u.nombre} cambió su contraseña.", {})
        bd.commit()
    return u


def _admins(bd: Session) -> int:
    return bd.execute(select(func.count()).select_from(Usuario)
                      .where(Usuario.rol == ROL_ADMIN, Usuario.activo.is_(True))).scalar_one()


# ---------------------------------------------------------------------------
# Lecturas para la pantalla
# ---------------------------------------------------------------------------
def _iso(f: datetime | None) -> str | None:
    f = _aware(f)
    return f.isoformat(timespec="seconds") if f else None


def usuario_dict(bd: Session, u: Usuario) -> dict[str, Any]:
    rol = ROLES.get(u.rol, {})
    cargadas = bd.execute(select(func.count()).select_from(Factura).where(Factura.cargada_por == u.correo)).scalar_one()
    firmas = bd.execute(select(func.count()).select_from(Aprobacion).where(Aprobacion.usuario_id == u.id)).scalar_one()
    sesiones = bd.execute(select(func.count()).select_from(Sesion)
                          .where(Sesion.usuario_id == u.id, Sesion.revocada.is_(False))).scalar_one()
    return {"id": u.id, "correo": u.correo, "nombre": u.nombre, "cargo": u.cargo, "rol": u.rol,
            "rol_nombre": rol.get("nombre", u.rol), "rol_descripcion": rol.get("descripcion", ""),
            "activo": u.activo, "mfa_activo": u.mfa_activo, "creado_en": _iso(u.creado_en),
            "ultimo_acceso": _iso(u.ultimo_acceso), "bloqueado": bool(u.bloqueado_hasta and _aware(u.bloqueado_hasta) > ahora()),
            "intentos_fallidos": u.intentos_fallidos, "facturas_cargadas": cargadas, "firmas": firmas,
            "sesiones_abiertas": sesiones}


def invitacion_dict(inv: Invitacion) -> dict[str, Any]:
    estado = ("usada" if inv.usada_en else "revocada" if inv.revocada
              else "vencida" if _aware(inv.expira_en) < ahora() else "pendiente")
    return {"id": inv.id, "correo": inv.correo, "nombre": inv.nombre, "cargo": inv.cargo, "rol": inv.rol,
            "rol_nombre": ROLES.get(inv.rol, {}).get("nombre", inv.rol), "prefijo": inv.prefijo, "estado": estado,
            "creada_por": inv.creada_por, "creada_en": _iso(inv.creada_en), "expira_en": _iso(inv.expira_en),
            "usada_en": _iso(inv.usada_en), "intentos": inv.intentos}


def listar(bd: Session) -> dict[str, Any]:
    usuarios = bd.execute(select(Usuario).order_by(Usuario.nombre)).scalars().all()
    invitaciones = bd.execute(select(Invitacion).order_by(Invitacion.id.desc()).limit(40)).scalars().all()
    por_rol: dict[str, int] = {}
    for u in usuarios:
        if u.activo:
            por_rol[u.rol] = por_rol.get(u.rol, 0) + 1
    return {
        "usuarios": [usuario_dict(bd, u) for u in usuarios],
        "invitaciones": [invitacion_dict(i) for i in invitaciones],
        "roles": [{"id": k, "nombre": v["nombre"], "descripcion": v["descripcion"],
                   "permisos": ([etiqueta(x) for x in sorted(v["permisos"]) if x != "*"] or ["Todos los permisos"]),
                   "personas": por_rol.get(k, 0)} for k, v in ROLES.items()],
        "politica_contrasena": {"largo_minimo": contrasenas.LARGO_MINIMO,
                                "texto": f"Al menos {contrasenas.LARGO_MINIMO} caracteres. Sin reglas de composición "
                                         "ni caducidad forzada (NIST SP 800-63B-4); se rechazan las contraseñas comunes."},
        "dias_invitacion": DIAS_INVITACION,
    }
