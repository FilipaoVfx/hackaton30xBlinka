"""
Control de acceso por roles (RBAC) con mínimo privilegio y segregación de funciones.

Nadie tiene todo: quien carga facturas no las aprueba, quien aprueba no cambia cuentas bancarias
sin verificación de otra persona, y el auditor solo lee. Los permisos se revisan en el servidor
en cada petición (la pantalla solo oculta botones; la seguridad real está aquí).
"""
from __future__ import annotations

ROLES: dict[str, dict] = {
    # Tres personas. Ninguna tiene todo: el CTO carga y administra pero no firma; CFO y CEO firman pero no cargan.
    # Las facturas sobre el umbral necesitan la firma de las dos personas que firman (doble control).
    "cfo": {"nombre": "CFO", "descripcion": "Firma lo que Kauta escala, edita reglas, fondea la wallet y verifica cuentas.",
            "permisos": {"ver", "facturas.aprobar", "reglas.editar", "cuentas.verificar", "wallet.fondear",
                         "pagos.reintentar", "simulador.usar", "auditoria.ver", "auditoria.exportar"}},
    "ceo": {"nombre": "CEO", "descripcion": "Segunda firma sobre el umbral; ve el resumen y exporta la auditoría.",
            "permisos": {"ver", "facturas.aprobar", "simulador.usar", "auditoria.ver", "auditoria.exportar"}},
    # Rol de administración técnica: «usuarios.gestionar» solo existe por API (no hay pantalla de personas sin login)
    "cto": {"nombre": "CTO", "descripcion": "Carga facturas, opera el agente, la seguridad y la demo; no firma pagos.",
            "permisos": {"ver", "facturas.cargar", "cuentas.solicitar", "simulador.usar", "auditoria.ver",
                         "auditoria.exportar", "usuarios.ver", "usuarios.gestionar", "demo.restablecer"}},
}
ROL_ADMIN = "cto"


# Cómo se le explica cada permiso a una persona que no programa
ETIQUETAS: dict[str, str] = {
    "ver": "Ver todo",
    "facturas.cargar": "Cargar facturas",
    "facturas.aprobar": "Aprobar o rechazar",
    "reglas.editar": "Editar las reglas",
    "cuentas.verificar": "Verificar cambios de cuenta",
    "cuentas.solicitar": "Solicitar cambios de datos",
    "wallet.fondear": "Fondear la wallet",
    "pagos.reintentar": "Reintentar pagos devueltos",
    "simulador.usar": "Usar el simulador",
    "auditoria.ver": "Ver la auditoría",
    "auditoria.exportar": "Exportar la auditoría",
    "usuarios.ver": "Ver las personas",
    "usuarios.gestionar": "Invitar personas y cambiar roles",
    "demo.restablecer": "Restablecer la demo",
}


def etiqueta(permiso: str) -> str:
    return ETIQUETAS.get(permiso, permiso)


def tiene(rol: str, permiso: str) -> bool:
    p = ROLES.get(rol, {}).get("permisos", set())
    return "*" in p or permiso in p or (permiso == "ver" and bool(p))


def permisos_de(rol: str) -> list[str]:
    p = ROLES.get(rol, {}).get("permisos", set())
    todos = sorted({x for r in ROLES.values() for x in r["permisos"] if x != "*"})
    return todos if "*" in p else sorted(p)
