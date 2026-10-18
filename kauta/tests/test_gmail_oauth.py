"""Regresión: el retorno de Google debe atenderlo Kauta, sin depender del localhost del usuario."""
import json
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from servidor.main import app
from servidor.servicios import gmail_oauth as oauth
from servidor.servicios.gmail import ErrorGmail, LECTURA


@pytest.fixture
def configurada(tmp_path, monkeypatch):
    monkeypatch.setattr(oauth, "CLIENTE", tmp_path / "web.json")
    monkeypatch.setattr(oauth, "PUERTA", tmp_path / "puerta.json")
    monkeypatch.setattr(oauth, "CALLBACK", "https://kauta.example/api/correo/oauth/callback")
    monkeypatch.setattr(oauth, "PENDIENTES", {})
    monkeypatch.setattr(oauth, "CONFIG_GMAIL", replace(oauth.CONFIG_GMAIL, credenciales=tmp_path / "gmail.json"))
    oauth.CLIENTE.write_text(json.dumps({"web": {"client_id": "cliente-prueba", "client_secret": "secreto-prueba",
                                                "redirect_uris": [oauth.CALLBACK]}}))
    return tmp_path


def comenzar():
    clave = oauth.crear_enlace().split("#", 1)[1]
    url, cookie = oauth.iniciar(clave)
    return clave, parse_qs(urlparse(url).query), cookie


def test_callback_https_no_cae_en_la_pantalla_spa():
    with TestClient(app) as c:
        r = c.get("/api/correo/oauth/callback?error=access_denied&state=desconocido")
    assert r.status_code == 400
    assert "autorización" in r.text.lower()


def test_retorno_https_sin_localhost_y_enlace_de_un_solo_uso(configurada):
    clave, p, _ = comenzar()
    assert p["redirect_uri"] == [oauth.CALLBACK]
    assert "127.0.0.1" not in p["redirect_uri"][0]
    assert p["scope"] == [LECTURA] and p["code_challenge_method"] == ["S256"]
    assert clave not in oauth.PUERTA.read_text()
    with pytest.raises(ErrorGmail, match="enlace"):
        oauth.iniciar(clave)


def test_conexion_ajena_no_puede_iniciar(configurada):
    oauth.crear_enlace()
    with pytest.raises(ErrorGmail, match="enlace"):
        oauth.iniciar("clave-ajena")


def test_cliente_de_escritorio_se_rechaza_antes_de_google(configurada):
    oauth.CLIENTE.write_text(json.dumps({"installed": {"client_id": "desktop", "client_secret": "secreto"}}))
    clave = oauth.crear_enlace().split("#")[1]
    with pytest.raises(ErrorGmail, match="Aplicación web"):
        oauth.iniciar(clave)


def test_uri_no_registrada_se_rechaza(configurada):
    oauth.CLIENTE.write_text(json.dumps({"web": {"client_id": "web", "client_secret": "secreto", "redirect_uris": []}}))
    clave = oauth.crear_enlace().split("#")[1]
    with pytest.raises(ErrorGmail, match="URI"):
        oauth.iniciar(clave)


def test_callback_requiere_el_mismo_navegador(configurada):
    _, p, cookie = comenzar()
    state = p["state"][0]
    with pytest.raises(ErrorGmail, match="otro navegador"):
        oauth.completar(state, "cookie-ajena", "codigo")
    assert state in oauth.PENDIENTES  # un tercero no puede consumir la autorización del usuario
    with pytest.raises(ErrorGmail, match="Google no completó"):
        oauth.completar(state, cookie, "", "access_denied")


def test_autorizacion_expirada_no_intercambia_codigo(configurada):
    _, p, cookie = comenzar()
    oauth.PENDIENTES[p["state"][0]]["vence"] = time.time() - 1
    with pytest.raises(ErrorGmail, match="venció"):
        oauth.completar(p["state"][0], cookie, "codigo")
    assert not oauth.CONFIG_GMAIL.credenciales.exists()


def test_google_verifica_cuenta_y_guarda_credencial_privada(configurada, monkeypatch):
    solicitudes = []
    def google(url, **kwargs):
        solicitudes.append((url, kwargs))
        if url.endswith("/token"):
            return {"access_token": "acceso-secreto", "refresh_token": "renovacion-secreta", "scope": LECTURA}
        return {"emailAddress": oauth.CONFIG_GMAIL.cuenta}
    monkeypatch.setattr(oauth, "solicitar_json", google)
    _, p, cookie = comenzar()
    oauth.completar(p["state"][0], cookie, "codigo-privado")
    guardado = json.loads(oauth.CONFIG_GMAIL.credenciales.read_text())
    assert guardado["refresh_token"] == "renovacion-secreta"
    assert oauth.CONFIG_GMAIL.credenciales.stat().st_mode & 0o777 == 0o600
    enviado = parse_qs(solicitudes[0][1]["datos"].decode())
    assert enviado["redirect_uri"] == [oauth.CALLBACK] and enviado["code_verifier"]
    with pytest.raises(ErrorGmail):
        oauth.completar(p["state"][0], cookie, "codigo-privado")


def test_cuenta_equivocada_no_se_guarda(configurada, monkeypatch):
    def google(url, **kwargs):
        if url.endswith("/token"):
            return {"access_token": "acceso", "refresh_token": "renovacion", "scope": LECTURA}
        return {"emailAddress": "otra@example.test"}
    monkeypatch.setattr(oauth, "solicitar_json", google)
    _, p, cookie = comenzar()
    with pytest.raises(ErrorGmail, match="otra cuenta"):
        oauth.completar(p["state"][0], cookie, "codigo")
    assert not oauth.CONFIG_GMAIL.credenciales.exists()


def test_api_cookie_segura_y_error_sin_exponer_codigo(configurada):
    clave = oauth.crear_enlace().split("#")[1]
    with TestClient(app, base_url="https://testserver") as c:
        r = c.post("/api/correo/oauth/iniciar", json={"clave": clave})
        assert r.status_code == 200
        cookie = r.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        state = parse_qs(urlparse(r.json()["url"]).query)["state"][0]
        r = c.get("/api/correo/oauth/callback", params={"state": state, "error": "access_denied", "code": "codigo-privado"})
        assert r.status_code == 400
        assert "codigo-privado" not in r.text and "secreto-prueba" not in r.text
