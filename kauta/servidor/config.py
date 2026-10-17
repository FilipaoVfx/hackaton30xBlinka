"""
Configuración del servidor. Todo sale de variables de entorno; nada sensible va en el código.

KAUTA_MODO            demo (por defecto) | produccion
KAUTA_BD              URL de la base de datos (SQLite en demo, PostgreSQL en producción)
KAUTA_CLAVE_DATOS     clave AES-256 en Base64 (32 bytes) para cifrar cuentas bancarias y secretos MFA
KAUTA_CLAVE_FIRMA     clave HMAC en Base64 para firmar aprobaciones y órdenes de pago
KAUTA_CLAVE_AUDITORIA clave HMAC en Base64 para encadenar el registro de auditoría
KAUTA_ORIGEN          origen público permitido (p. ej. https://kauta.ejemplo.com)
ANTHROPIC_API_KEY     opcional: activa la lectura con IA de documentos nuevos

En modo demo, si faltan las claves se generan al azar y se guardan en var/ con permisos 600.
En producción, si falta una clave el servidor NO arranca (las claves viven en un KMS o gestor de secretos).
"""
from __future__ import annotations

import base64
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VAR = Path(os.environ.get("KAUTA_VAR", RAIZ / "var"))


def _clave(nombre: str, modo: str) -> bytes:
    valor = os.environ.get(nombre)
    if valor:
        clave = base64.b64decode(valor)
        if len(clave) < 32:
            raise RuntimeError(f"{nombre} debe tener al menos 32 bytes.")
        return clave
    if modo == "produccion":
        raise RuntimeError(f"Falta {nombre}. En producción las claves vienen del gestor de secretos, nunca del disco.")
    VAR.mkdir(parents=True, exist_ok=True)
    ruta = VAR / f"{nombre.lower()}.key"
    if not ruta.exists():
        ruta.write_bytes(base64.b64encode(secrets.token_bytes(32)))
        os.chmod(ruta, 0o600)
    return base64.b64decode(ruta.read_bytes())


@dataclass(frozen=True)
class Config:
    modo: str
    url_bd: str
    clave_datos: bytes
    clave_firma: bytes
    clave_auditoria: bytes
    origen: str
    cookie_segura: bool
    origenes_adicionales: tuple[str, ...] = ()
    preparar_recorrido: bool = False
    inactividad_min: int = 30
    duracion_max_h: int = 8
    max_archivo_mb: int = 10
    version: str = "2.1.0"

    @property
    def demo(self) -> bool:
        return self.modo != "produccion"

    @property
    def nombre_cookie(self) -> str:
        # El prefijo __Host- obliga a Secure, Path=/ y sin Domain: la cookie no se comparte con subdominios
        return "__Host-kauta_sesion" if self.cookie_segura else "kauta_sesion"


def cargar() -> Config:
    modo = os.environ.get("KAUTA_MODO", "demo")
    VAR.mkdir(parents=True, exist_ok=True)
    origen = os.environ.get("KAUTA_ORIGEN", "http://localhost:8000")
    return Config(
        modo=modo,
        url_bd=os.environ.get("KAUTA_BD", f"sqlite:///{VAR / 'kauta.db'}"),
        clave_datos=_clave("KAUTA_CLAVE_DATOS", modo),
        clave_firma=_clave("KAUTA_CLAVE_FIRMA", modo),
        clave_auditoria=_clave("KAUTA_CLAVE_AUDITORIA", modo),
        origen=origen.rstrip("/"),
        cookie_segura=origen.startswith("https://"),
        origenes_adicionales=tuple(x.strip().rstrip("/") for x in os.environ.get("KAUTA_ORIGENES_ADICIONALES", "").split(",") if x.strip()),
        preparar_recorrido=os.environ.get("KAUTA_PREPARAR_RECORRIDO", "0") == "1",
    )


CONFIG = cargar()
