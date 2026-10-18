#!/usr/bin/env python3
"""Autoriza Gmail readonly mediante OAuth de aplicación de escritorio y callback local.

Ejecutar en el equipo donde se abre el navegador. No usa contraseñas de Gmail.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def conectar(cliente: Path, destino: Path, cuenta: str, puerto: int, sin_navegador: bool):
    config = json.loads(cliente.read_text()).get("installed")
    if not config or not config.get("client_id") or not config.get("client_secret"):
        raise ValueError("Use el JSON de un cliente OAuth de tipo Aplicación de escritorio, con Gmail API habilitada.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    resultado = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path != "/oauth2callback" or not secrets.compare_digest(q.get("state", [""])[0], state):
                self.send_error(400, "Solicitud no valida")
                return
            resultado.update({"code": q.get("code", [""])[0], "error": q.get("error", [""])[0]})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write("Autorización recibida. Puede volver a la terminal de Kauta.".encode())

        def log_message(self, *_):
            pass  # el código OAuth nunca aparece en logs

    with HTTPServer(("127.0.0.1", puerto), Callback) as servidor:
        redirect = f"http://127.0.0.1:{servidor.server_port}/oauth2callback"
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": config["client_id"], "redirect_uri": redirect, "response_type": "code",
            "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
            "login_hint": cuenta, "code_challenge": challenge, "code_challenge_method": "S256",
        })
        print("Abra este enlace en el navegador del mismo equipo (vence en 5 minutos):\n" + url, flush=True)
        if not sin_navegador:
            webbrowser.open(url)
        servidor.timeout = 1
        limite = time.monotonic() + 300
        while not resultado and time.monotonic() < limite:
            servidor.handle_request()
    if not resultado.get("code") or resultado.get("error"):
        raise ValueError("La autorización no se completó. No se guardaron credenciales.")
    datos = urlencode({"client_id": config["client_id"], "client_secret": config["client_secret"],
                       "code": resultado["code"], "code_verifier": verifier, "grant_type": "authorization_code",
                       "redirect_uri": redirect}).encode()
    with urlopen(Request("https://oauth2.googleapis.com/token", data=datos,
                         headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=20) as r:
        token = json.load(r)
    if not token.get("refresh_token") or SCOPE not in token.get("scope", "").split():
        raise ValueError("Google no concedió el permiso de lectura permanente. No se guardaron credenciales.")
    with urlopen(Request("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                         headers={"Authorization": "Bearer " + token["access_token"]}), timeout=20) as r:
        perfil = json.load(r)
    if perfil.get("emailAddress", "").lower() != cuenta.lower():
        raise ValueError("Se autorizó otra cuenta. No se guardaron credenciales.")
    salida = {"type": "authorized_user", "client_id": config["client_id"], "client_secret": config["client_secret"],
              "refresh_token": token["refresh_token"], "scopes": [SCOPE]}
    destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporal = destino.with_name(destino.name + ".tmp-" + secrets.token_hex(6))
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as archivo:
        json.dump(salida, archivo)
    os.replace(temporal, destino)
    print(f"Cuenta verificada: {cuenta}. Credencial guardada en {destino} con permisos 600. No la suba a Git.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cliente", type=Path, required=True, help="JSON OAuth de Aplicación de escritorio")
    p.add_argument("--destino", type=Path, required=True, help="Ruta privada del JSON autorizado")
    p.add_argument("--cuenta", default="felipearango306@gmail.com")
    p.add_argument("--puerto", type=int, default=8765)
    p.add_argument("--sin-navegador", action="store_true")
    a = p.parse_args()
    try:
        conectar(a.cliente, a.destino, a.cuenta, a.puerto, a.sin_navegador)
    except HTTPError as e:
        print(f"Google denegó la operación (HTTP {e.code}). Revise Gmail API, el cliente OAuth y los usuarios de prueba.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(str(e) if isinstance(e, ValueError) else "No se pudo completar la conexión OAuth.", file=sys.stderr)
        sys.exit(1)
