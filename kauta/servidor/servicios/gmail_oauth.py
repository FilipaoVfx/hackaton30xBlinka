"""Autorización de Gmail para servidor remoto: callback HTTPS, PKCE y enlace privado de un uso."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

from ..config import CONFIG, VAR
from .gmail import LECTURA, ErrorGmail, solicitar_json
from .ingesta import CONFIG_GMAIL

CALLBACK = CONFIG.origen + "/api/correo/oauth/callback"
CLIENTE = CONFIG_GMAIL.credenciales.with_name("oauth-client-web.json")
PUERTA = VAR / "gmail-conexion.json"
COOKIE = "kauta_gmail_oauth"
PENDIENTES: dict[str, dict] = {}
CANDADO = threading.RLock()


def guardar_privado(ruta: Path, datos: dict):
    ruta.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporal = ruta.with_name(ruta.name + ".tmp-" + secrets.token_hex(8))
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(datos, f)
    os.replace(temporal, ruta)


def crear_enlace():
    """Solo se invoca desde la terminal privada del servidor; nunca desde la demo pública."""
    clave = secrets.token_urlsafe(32)
    guardar_privado(PUERTA, {"hash": hashlib.sha256(clave.encode()).hexdigest(),
                            "vence": time.time() + 1800, "usado": False})
    return CONFIG.origen + "/api/correo/oauth/conectar#" + clave


def _cliente():
    try:
        c = json.loads(CLIENTE.read_text()).get("web", {})
    except (OSError, ValueError):
        c = {}
    if not c.get("client_id") or not c.get("client_secret"):
        raise ErrorGmail("Falta el cliente OAuth de tipo Aplicación web. El cliente de escritorio no sirve para este retorno HTTPS.")
    if CALLBACK not in c.get("redirect_uris", []):
        raise ErrorGmail("Añada esta URI de redirección autorizada al cliente web: " + CALLBACK)
    return c


def iniciar(clave: str):
    with CANDADO:
        try:
            p = json.loads(PUERTA.read_text())
        except (OSError, ValueError):
            p = {}
        if (not clave or len(clave) > 200 or p.get("usado") or p.get("vence", 0) < time.time()
                or not hmac.compare_digest(p.get("hash", ""), hashlib.sha256(clave.encode()).hexdigest())):
            raise ErrorGmail("El enlace de conexión no es válido o venció. Solicite uno nuevo al administrador.")
        c = _cliente()
        state, cookie, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        for k in list(PENDIENTES):
            if PENDIENTES[k]["vence"] < time.time():
                del PENDIENTES[k]
        PENDIENTES[state] = {"cookie": cookie, "verifier": verifier, "vence": time.time() + 600,
                             "client_id": c["client_id"], "client_secret": c["client_secret"]}
        p["usado"] = True
        guardar_privado(PUERTA, p)
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": c["client_id"], "redirect_uri": CALLBACK, "response_type": "code", "scope": LECTURA,
            "access_type": "offline", "prompt": "consent", "state": state,
            "login_hint": CONFIG_GMAIL.cuenta, "code_challenge": challenge, "code_challenge_method": "S256",
        })
        return url, cookie


def completar(state: str, cookie: str, code: str, error: str = ""):
    with CANDADO:
        p = PENDIENTES.get(state)
        if not p or p["vence"] < time.time() or not cookie or not hmac.compare_digest(p["cookie"], cookie):
            raise ErrorGmail("La autorización venció o pertenece a otro navegador. Solicite un enlace nuevo.")
        del PENDIENTES[state]  # un solo intento; no se pueden repetir códigos ni callbacks
    if error or not code:
        raise ErrorGmail("Google no completó la autorización. Vuelva a conectar y acepte el permiso de lectura.")
    token = solicitar_json("https://oauth2.googleapis.com/token", datos=urlencode({
        "client_id": p["client_id"], "client_secret": p["client_secret"], "code": code,
        "code_verifier": p["verifier"], "grant_type": "authorization_code", "redirect_uri": CALLBACK,
    }).encode(), cabeceras={"Content-Type": "application/x-www-form-urlencoded"})
    if not token.get("refresh_token") or not token.get("access_token") or LECTURA not in token.get("scope", "").split():
        raise ErrorGmail("Google no concedió la lectura permanente de Gmail. Vuelva a conectar.")
    perfil = solicitar_json("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                             cabeceras={"Authorization": "Bearer " + token["access_token"]})
    if perfil.get("emailAddress", "").lower() != CONFIG_GMAIL.cuenta:
        raise ErrorGmail("Se autorizó otra cuenta. Conecte " + CONFIG_GMAIL.cuenta + ".")
    guardar_privado(CONFIG_GMAIL.credenciales, {"type": "authorized_user", "client_id": p["client_id"],
                    "client_secret": p["client_secret"], "refresh_token": token["refresh_token"], "scopes": [LECTURA]})
