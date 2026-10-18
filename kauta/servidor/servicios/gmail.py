"""Cliente Gmail de solo lectura. Las credenciales del chat y de Drive no se reutilizan."""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import VAR

LECTURA = "https://www.googleapis.com/auth/gmail.readonly"
API = "https://gmail.googleapis.com/gmail/v1/users/me"


class ErrorGmail(ValueError):
    """Mensaje público sin cuerpos de respuesta, tokens ni datos de la cuenta."""


@dataclass(frozen=True)
class ConfigGmail:
    activo: bool = False
    cuenta: str = "felipearango306@gmail.com"
    asunto: str = "kauta"
    intervalo: int = 60
    credenciales: Path = VAR / "gmail-oauth.json"
    desde: str = ""
    max_mensaje_mb: int = 25

    @classmethod
    def cargar(cls):
        return cls(
            activo=os.environ.get("KAUTA_GMAIL_ACTIVO", "0") == "1",
            cuenta=os.environ.get("KAUTA_GMAIL_CUENTA", "felipearango306@gmail.com").strip().lower(),
            intervalo=max(30, int(os.environ.get("KAUTA_GMAIL_INTERVALO", "60"))),
            credenciales=Path(os.environ.get("KAUTA_GMAIL_CREDENCIALES", str(VAR / "gmail-oauth.json"))),
            desde=os.environ.get("KAUTA_GMAIL_DESDE", ""),
        )


def solicitar_json(url: str, *, datos: bytes | None = None, cabeceras: dict | None = None, max_bytes=40 * 1024 * 1024):
    try:
        with urlopen(Request(url, data=datos, headers=cabeceras or {}), timeout=20) as respuesta:
            cuerpo = respuesta.read(max_bytes + 1)
        if len(cuerpo) > max_bytes:
            raise ErrorGmail("La respuesta de Gmail supera el tamaño permitido.")
        return json.loads(cuerpo)
    except HTTPError as e:
        if e.code in (400, 401):
            raise ErrorGmail("Gmail requiere renovar la autorización OAuth de solo lectura.") from None
        if e.code == 403:
            raise ErrorGmail("Google denegó el acceso: revise Gmail API y el permiso gmail.readonly.") from None
        if e.code == 404:
            raise ErrorGmail("El mensaje ya no está disponible en Gmail.") from None
        if e.code == 429 or e.code >= 500:
            raise ErrorGmail("Gmail no está disponible temporalmente; se reintentará en la próxima consulta.") from None
        raise ErrorGmail(f"Gmail devolvió un error HTTP {e.code}.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ErrorGmail("No se pudo completar la conexión con Gmail; se reintentará.") from None


class Gmail:
    def __init__(self, config: ConfigGmail):
        self.config = config
        self._token = ""
        self._vence = 0.0

    def _acceso(self):
        if self._token and time.monotonic() < self._vence:
            return self._token
        try:
            c = json.loads(self.config.credenciales.read_text())
            if not all(c.get(k) for k in ("client_id", "client_secret", "refresh_token")):
                raise ValueError()
        except (OSError, ValueError):
            raise ErrorGmail("Falta la credencial OAuth de Gmail para el servidor. Conecte la cuenta con gmail.readonly.") from None
        # URL fija: un archivo de credenciales no puede redirigir el refresh token a otro servidor.
        r = solicitar_json("https://oauth2.googleapis.com/token", datos=urlencode({
            "client_id": c["client_id"], "client_secret": c["client_secret"],
            "refresh_token": c["refresh_token"], "grant_type": "refresh_token",
        }).encode(), cabeceras={"Content-Type": "application/x-www-form-urlencoded"})
        if not r.get("access_token"):
            raise ErrorGmail("Google no entregó un token de acceso. Renueve la autorización.")
        self._token = r["access_token"]
        self._vence = time.monotonic() + max(0, int(r.get("expires_in", 3600)) - 60)
        return self._token

    def _get(self, ruta: str, **params):
        try:
            return solicitar_json(API + ruta + ("?" + urlencode(params) if params else ""),
                                  cabeceras={"Authorization": "Bearer " + self._acceso()})
        except ErrorGmail:
            self._token = ""
            raise

    def perfil(self):
        r = self._get("/profile")
        if r.get("emailAddress", "").lower() != self.config.cuenta:
            raise ErrorGmail("La credencial pertenece a otra cuenta. La escucha se detuvo sin importar mensajes.")
        return r

    def listar(self, consulta: str, pagina: str = ""):
        params = {"q": consulta, "maxResults": 100}
        if pagina:
            params["pageToken"] = pagina
        return self._get("/messages", **params)

    def metadatos(self, mensaje_id: str):
        return self._get("/messages/" + mensaje_id, format="metadata")

    def original(self, mensaje_id: str):
        r = self._get("/messages/" + mensaje_id, format="raw")
        raw = r.get("raw", "")
        if not raw:
            raise ErrorGmail("Gmail no devolvió el correo original.")
        if len(raw) > self.config.max_mensaje_mb * 1024 * 1024 * 4 // 3 + 4:
            raise ErrorGmail("El correo supera el límite de recepción.")
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
