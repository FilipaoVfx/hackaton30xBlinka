"""Contrato de Gmail: cuenta correcta, filtro, reinicios, errores y cero decisiones duplicadas."""
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from servidor.db import Base
from servidor.ingesta_modelos import CorreoRecibido, DocumentoRecibido, FuenteCorreo
from servidor.modelos import EventoAuditoria, Factura, Pago
from servidor.servicios import agente, auditoria, ingesta, semilla
from servidor.servicios.gmail import ConfigGmail, ErrorGmail, Gmail

DATA = Path(__file__).resolve().parents[1] / "data"
XML = (DATA / "sorpresa/S01_traducciones-maya_TM-455.xml").read_bytes()
FECHA = datetime(2026, 10, 17, 21, 0, tzinfo=timezone.utc)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/correo.db")
    Base.metadata.create_all(engine)
    sesiones = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(ingesta, "SesionBD", sesiones)
    monkeypatch.setattr(ingesta, "VAR", tmp_path)
    monkeypatch.setattr(semilla, "motor_bd", engine)
    with sesiones() as bd:
        semilla.iniciar(bd, con_set=False)
    config = ConfigGmail(activo=True, desde="2026-10-17T00:00:00Z", credenciales=tmp_path / "oauth.json")
    yield sesiones, config, tmp_path
    engine.dispose()


def correo(asunto="kauta · prueba", adjuntos=None, cuerpo="Cuenta de cobro ficticia."):
    m = EmailMessage()
    m["From"] = "Proveedor de prueba <proveedor@example.test>"
    m["To"] = "felipearango306@gmail.com"
    m["Subject"] = asunto
    m.set_content(cuerpo)
    for nombre, contenido, mime in (adjuntos if adjuntos is not None else [("factura.xml", XML, "application/xml")]):
        a, b = mime.split("/")
        m.add_attachment(contenido, maintype=a, subtype=b, filename=nombre)
    return m.as_bytes()


def meta(mid="m1", **extra):
    return {"id": mid, "threadId": "t1", "labelIds": ["INBOX"],
            "internalDate": str(int(FECHA.timestamp() * 1000)), "sizeEstimate": 1000, **extra}


class Buzon:
    def __init__(self, mensajes=None):
        self.mensajes = mensajes or {"m1": correo()}
        self.consultas = []
        self.descargas = 0

    def perfil(self):
        return {"emailAddress": "felipearango306@gmail.com"}

    def listar(self, q, pagina=""):
        self.consultas.append((q, pagina))
        # Una página por mensaje prueba que se recorre la paginación.
        indice = int(pagina or 0)
        ids = list(self.mensajes)
        return {"messages": [{"id": ids[indice]}] if indice < len(ids) else [],
                "nextPageToken": str(indice + 1) if indice + 1 < len(ids) else ""}

    def metadatos(self, mid):
        return meta(mid)

    def original(self, mid):
        self.descargas += 1
        return self.mensajes[mid]


def test_gmail_idempotencia_original_y_auditoria(entorno):
    sesiones, config, tmp = entorno
    buzon = Buzon()
    ingesta.ejecutar(config, buzon)
    with sesiones() as bd:
        f = bd.scalar(select(Factura))
        d = bd.scalar(select(DocumentoRecibido))
        c = bd.scalar(select(CorreoRecibido))
        assert f and f.origen == "gmail" and d.factura_id == f.id
        assert f.cargada_por == "proveedor@example.test"
        assert Path(c.ruta_original).read_bytes() == buzon.mensajes["m1"]
        assert (Path(c.ruta_original).stat().st_mode & 0o777) == 0o600
        assert auditoria.verificar(bd)["ok"]
        assert bd.get(FuenteCorreo, config.cuenta).ultimo_exito is not None
    ingesta.ejecutar(config, buzon)
    with sesiones() as bd:
        assert bd.scalar(select(func.count()).select_from(Factura)) == 1
        assert bd.scalar(select(func.count()).select_from(CorreoRecibido)) == 1
    assert buzon.descargas == 1
    assert all("in:inbox subject:kauta after:" in q and "is:unread" not in q for q, _ in buzon.consultas)


def test_reenvio_identico_no_repite_decision_y_pagina(entorno):
    sesiones, config, _ = entorno
    buzon = Buzon({"m1": correo(), "m2": correo()})
    ingesta.ejecutar(config, buzon)
    with sesiones() as bd:
        assert bd.scalar(select(func.count()).select_from(Factura)) == 1
        assert bd.scalar(select(func.count()).select_from(CorreoRecibido)) == 2
        ds = bd.scalars(select(DocumentoRecibido).order_by(DocumentoRecibido.id)).all()
        assert [d.estado for d in ds] == ["procesado", "duplicado"]
        assert ds[0].factura_id == ds[1].factura_id
    assert buzon.consultas[1][1] == "1"


@pytest.mark.parametrize("asunto,labels", [("Factura sin filtro", ["INBOX"]), ("kauda", ["INBOX"]), ("kauta", [])])
def test_filtro_se_verifica_en_original_y_bandeja(entorno, asunto, labels):
    sesiones, config, _ = entorno
    with sesiones() as bd:
        assert ingesta.recibir(bd, meta(labelIds=labels), correo(asunto=asunto), config) is None
        assert bd.scalar(select(func.count()).select_from(CorreoRecibido)) == 0


def test_varias_facturas_pdf_xml_soporte_y_formatos_no_compatibles(entorno):
    sesiones, config, _ = entorno
    raw = correo(asunto="KAUTA · lote", adjuntos=[("uno.xml", XML, "application/xml"),
        ("uno.pdf", b"%PDF-ficticio", "application/pdf"),
        ("dos.xml", XML.replace(b'TM-455', b'TM-456'), "application/xml"),
        ("notas.xlsx", b"datos", "application/octet-stream")])
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), raw, config)
        ds = bd.scalars(select(DocumentoRecibido).order_by(DocumentoRecibido.id)).all()
        assert [d.estado for d in ds] == ["recibido", "soporte", "recibido", "revision"]
        assert all(d.ruta for d in ds)


def test_cuerpo_sin_adjuntos_se_conserva_para_lectura(entorno):
    sesiones, config, _ = entorno
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), correo(adjuntos=[]), config)
        d = bd.scalar(select(DocumentoRecibido))
        assert d.parte == "cuerpo" and d.nombre.endswith(".eml")
        assert "Cuenta de cobro ficticia" in Path(d.ruta).read_text()


def test_nombre_de_referencia_no_habilita_datos_ficticios(entorno, monkeypatch):
    sesiones, config, _ = entorno
    nombres = []
    def lector(nombre, _):
        nombres.append(nombre)
        raise agente.ErrorNegocio("No se pudo leer con confianza.")
    monkeypatch.setattr(agente.EXTRACTOR, "extraer", lector)
    raw = correo(adjuntos=[("F01_nube-clara_INV-1001.pdf", b"%PDF-falso", "application/pdf")])
    ingesta.ejecutar(config, Buzon({"m1": raw}))
    with sesiones() as bd:
        assert bd.scalar(select(func.count()).select_from(Factura)) == 0
        d = bd.scalar(select(DocumentoRecibido))
        assert d.estado == "error_lectura" and d.intentos == 1
        ingesta.procesar_documento(bd, d.id, reintentar=True)
        assert d.intentos == 2
    assert all(n.startswith("gmail_") for n in nombres)


def test_fallo_transaccional_no_deja_factura_huerfana(entorno, monkeypatch):
    sesiones, config, _ = entorno
    original = auditoria.registrar
    def fallar(bd, tipo, *args, **kwargs):
        if tipo == "correo.documento_procesado":
            raise RuntimeError("Fallo simulado después de crear factura")
        return original(bd, tipo, *args, **kwargs)
    monkeypatch.setattr(auditoria, "registrar", fallar)
    ingesta.ejecutar(config, Buzon())
    with sesiones() as bd:
        assert bd.scalar(select(func.count()).select_from(Factura)) == 0
        assert bd.scalar(select(func.count()).select_from(Pago)) == 0
        d = bd.scalar(select(DocumentoRecibido))
        assert d.estado == "error_lectura" and d.factura_id is None
        assert auditoria.verificar(bd)["ok"]
        monkeypatch.setattr(auditoria, "registrar", original)
        ingesta.procesar_documento(bd, d.id, reintentar=True)
        assert d.estado == "procesado"
        assert bd.scalar(select(func.count()).select_from(Factura)) == 1


def test_reinicio_procesa_recepcion_pendiente(entorno):
    sesiones, config, _ = entorno
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), correo(), config)
    ingesta.ejecutar(config, Buzon())
    with sesiones() as bd:
        assert bd.scalar(select(DocumentoRecibido)).estado == "procesado"


def test_no_avanza_cursor_si_gmail_falla(entorno):
    sesiones, config, _ = entorno
    class Caido(Buzon):
        def listar(self, *_):
            raise ErrorGmail("Servicio no disponible.")
    ingesta.ejecutar(config, Caido())
    with sesiones() as bd:
        f = bd.get(FuenteCorreo, config.cuenta)
        assert f.cursor is None and f.ultimo_exito is None and f.error


def test_otra_cuenta_y_credencial_ausente_no_importan(entorno, monkeypatch):
    sesiones, config, _ = entorno
    real = Gmail(config)
    with pytest.raises(ErrorGmail, match="Falta la credencial"):
        real.perfil()
    monkeypatch.setattr(real, "_get", lambda *_: {"emailAddress": "otra@example.test"})
    with pytest.raises(ErrorGmail, match="otra cuenta"):
        real.perfil()
    ingesta.ejecutar(config, real)
    with sesiones() as bd:
        assert bd.scalar(select(func.count()).select_from(CorreoRecibido)) == 0
        assert ingesta.estado(bd, config)["estado"] == "requiere_autorizacion"


def test_mensaje_grande_deja_revision_sin_descargar(entorno):
    sesiones, config, _ = entorno
    class Grande(Buzon):
        def metadatos(self, mid):
            return meta(mid, sizeEstimate=30 * 1024 * 1024)
    buzon = Grande()
    ingesta.ejecutar(config, buzon)
    assert buzon.descargas == 0
    with sesiones() as bd:
        assert bd.scalar(select(DocumentoRecibido)).estado == "revision"


def test_estado_no_dice_escuchando_sin_conexion_exitosa(entorno):
    sesiones, config, _ = entorno
    config.credenciales.write_text("{}")
    with sesiones() as bd:
        assert ingesta.estado(bd, config)["estado"] == "sin_senal"
        assert "credenciales" not in ingesta.estado(bd, config)


def test_api_requiere_sesion_y_restringe_reintento_al_cto():
    from servidor.main import app
    from servidor.seguridad.limites import LIMITADOR
    with TestClient(app) as c:
        assert c.get("/api/correo/estado").status_code == 401
        LIMITADOR.reiniciar()
        r = c.post("/api/auth/persona", json={"correo": "carlos.rivera@brisamar.example"}, headers={"Origin": "http://localhost:8000"})
        assert r.status_code == 200
        csrf = r.json()["usuario"]["csrf"]
        assert c.get("/api/correo/estado").status_code == 200
        r = c.post("/api/correo/documentos/1/reintentar", json={}, headers={"Origin": "http://localhost:8000", "X-CSRF-Token": csrf})
        assert r.status_code == 403


@pytest.mark.parametrize("asunto", ["kauta", "Kauta", "KAUTA", "Factura KaUtA octubre"])
def test_keyword_kauta_no_distingue_mayusculas(entorno, asunto):
    sesiones, config, _ = entorno
    with sesiones() as bd:
        assert ingesta.recibir(bd, meta(), correo(asunto=asunto), config) is not None


def test_eliminar_pendiente_no_reimporta_y_audita_una_vez(entorno):
    sesiones, config, _ = entorno
    buzon = Buzon()
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), correo(), config)
        d = bd.scalar(select(DocumentoRecibido))
        did = d.id
        ingesta.eliminar_documento(bd, did, "CTO de prueba")
        ingesta.eliminar_documento(bd, did, "CTO de prueba")
        assert ingesta.documentos(bd, config.cuenta) == []
        assert ingesta.estado(bd, config)["documentos"] == {}
        eventos = bd.scalars(select(EventoAuditoria).where(EventoAuditoria.tipo == "correo.documento_eliminado")).all()
        assert len(eventos) == 1 and eventos[0].actor == "CTO de prueba"
        assert auditoria.verificar(bd)["ok"]
    ingesta.ejecutar(config, buzon)
    with sesiones() as bd:
        assert bd.get(DocumentoRecibido, did).estado == "eliminado"
        assert bd.scalar(select(func.count()).select_from(Factura)) == 0
    assert buzon.descargas == 0


def test_eliminar_recepcion_conserva_factura_pago_y_evidencia(entorno):
    sesiones, config, _ = entorno
    ingesta.ejecutar(config, Buzon())
    with sesiones() as bd:
        d = bd.scalar(select(DocumentoRecibido))
        fid, ruta = d.factura_id, d.ruta
        f = bd.get(Factura, fid)
        estado, decision = f.estado, f.decision
        pagos_antes = bd.scalar(select(func.count()).select_from(Pago))
        ingesta.eliminar_documento(bd, d.id, "CTO de prueba")
        assert ingesta.documentos(bd, config.cuenta) == []
        assert bd.get(Factura, fid).estado == estado and f.decision == decision
        assert bd.scalar(select(func.count()).select_from(Pago)) == pagos_antes
        assert Path(ruta).exists() and auditoria.verificar(bd)["ok"]


def test_sesion_antigua_no_procesa_documento_eliminado(entorno):
    sesiones, config, _ = entorno
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), correo(), config)
        d = bd.scalar(select(DocumentoRecibido))
        with sesiones() as otra:
            ingesta.eliminar_documento(otra, d.id, "CTO de prueba")
        ingesta.procesar_documento(bd, d.id, reintentar=True)
        assert bd.get(DocumentoRecibido, d.id).estado == "eliminado"
        assert bd.scalar(select(func.count()).select_from(Factura)) == 0


def test_api_eliminar_exige_cto_csrf_y_no_afecta_gmail(entorno):
    from servidor.db import obtener_bd
    from servidor.main import app
    from servidor.seguridad.limites import LIMITADOR
    sesiones, config, _ = entorno
    with sesiones() as bd:
        ingesta.recibir(bd, meta(), correo(), config)
        did = bd.scalar(select(DocumentoRecibido.id))
    def obtener_prueba():
        with sesiones() as bd:
            yield bd
    app.dependency_overrides[obtener_bd] = obtener_prueba
    origen = {"Origin": "http://localhost:8000"}
    try:
        with TestClient(app) as c:
            assert c.delete(f"/api/correo/documentos/{did}").status_code == 401
            LIMITADOR.reiniciar()
            r = c.post("/api/auth/persona", json={"correo": "carlos.rivera@brisamar.example"}, headers=origen)
            h = {**origen, "X-CSRF-Token": r.json()["usuario"]["csrf"]}
            assert c.delete(f"/api/correo/documentos/{did}", headers=h).status_code == 403
            r = c.post("/api/auth/persona", json={"correo": "tomas.herrera@brisamar.example"}, headers=origen)
            h = {**origen, "X-CSRF-Token": r.json()["usuario"]["csrf"]}
            assert c.delete(f"/api/correo/documentos/{did}", headers=origen).status_code == 403
            assert c.delete(f"/api/correo/documentos/{did}", headers=h).json()["estado"] == "eliminado"
            assert c.get("/api/correo/documentos").json() == []
            assert c.delete("/api/correo/documentos/999999", headers=h).status_code == 404
        with sesiones() as bd:
            assert bd.scalar(select(func.count()).select_from(CorreoRecibido)) == 1
    finally:
        app.dependency_overrides.pop(obtener_bd, None)
