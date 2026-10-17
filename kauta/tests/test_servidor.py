"""Pruebas del servidor: seguridad de la API, doble aprobación, wallet, idempotencia, auditoría y simulador."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
_TMP = tempfile.mkdtemp(prefix="kauta-test-")
os.environ["KAUTA_VAR"] = _TMP
os.environ["KAUTA_BD"] = f"sqlite:///{_TMP}/prueba.db"

from fastapi.testclient import TestClient  # noqa: E402

from servidor.main import app  # noqa: E402
from servidor.seguridad.limites import LIMITADOR  # noqa: E402

CLAVE = "Kauta-30X-demo-2026"
ORIGEN = {"Origin": "http://localhost:8000"}


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app, base_url="http://localhost:8000") as c:
        yield c
    shutil.rmtree(_TMP, ignore_errors=True)


def entrar(c, correo, clave=CLAVE):
    LIMITADOR.reiniciar()
    c.post("/api/auth/logout", headers=ORIGEN)
    r = c.post("/api/auth/login", json={"correo": correo, "contrasena": clave}, headers=ORIGEN)
    assert r.status_code == 200, r.text
    return {**ORIGEN, "X-CSRF-Token": r.json()["usuario"]["csrf"]}


def test_set_oficial_20_de_20(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    m = cliente.get("/api/resumen", headers=h).json()["metricas"]
    assert m["set_aciertos"] == 20 and m["pagos_fuera_de_reglas"] == 0 and m["trampas_detenidas"] == m["trampas_total"] == 11


def test_sin_sesion_y_sin_csrf(cliente):
    cliente.post("/api/auth/logout", headers=ORIGEN)
    assert cliente.get("/api/facturas").status_code == 401
    h = entrar(cliente, "mariana.torres@brisamar.example")
    r = cliente.post("/api/facturas/F09/rechazar", json={"comentario": "x"}, headers=ORIGEN)  # sin token CSRF
    assert r.status_code == 403
    r = cliente.post("/api/facturas/F09/rechazar", json={"comentario": "x"}, headers={**h, "Origin": "https://atacante.example"})
    assert r.status_code == 403


def test_contrasena_incorrecta_es_generica(cliente):
    LIMITADOR.reiniciar()
    r1 = cliente.post("/api/auth/login", json={"correo": "mariana.torres@brisamar.example", "contrasena": "mala"}, headers=ORIGEN)
    r2 = cliente.post("/api/auth/login", json={"correo": "nadie@x.example", "contrasena": "mala"}, headers=ORIGEN)
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()


def test_permisos_por_rol(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")  # CTO: no firma pagos
    r = cliente.post("/api/facturas/F09/aprobar", json={"comentario": "intento"}, headers=h)
    assert r.status_code == 403


def test_regla_dura_no_se_salta_aprobando(cliente):
    h = entrar(cliente, "mariana.torres@brisamar.example")
    r = cliente.post("/api/facturas/F10/aprobar", json={"comentario": "Conforme."}, headers=h)
    assert r.status_code == 409 and "R12" in r.json()["detail"]


def test_doble_aprobacion_y_firmas(cliente):
    h = entrar(cliente, "carlos.rivera@brisamar.example")
    d = cliente.get("/api/simulador/escenarios/supera_umbral?periodo=2026-11", headers=h).json()
    f = cliente.post("/api/simulador/factura", json=d, headers=h).json()
    assert f["estado"] == "pendiente" and f["aprobaciones_requeridas"] == 2
    r = cliente.post(f"/api/facturas/{f['id']}/aprobar", json={"comentario": "Primera firma."}, headers=h).json()
    assert r["completa"] is False
    r = cliente.post(f"/api/facturas/{f['id']}/aprobar", json={"comentario": "Otra vez yo."}, headers=h)
    assert r.status_code == 409  # la misma persona no firma dos veces
    h2 = entrar(cliente, "mariana.torres@brisamar.example")
    r = cliente.post(f"/api/facturas/{f['id']}/aprobar", json={"comentario": "Segunda firma."}, headers=h2).json()
    assert r["completa"] is True and r["pago"]
    det = cliente.get(f"/api/facturas/{f['id']}", headers=h2).json()
    assert det["estado"] == "pagada" and det["pago_detalle"]["estado"] == "liquidado"


def test_firma_alterada_bloquea_el_pago(cliente):
    from servidor.db import SesionBD
    from servidor.modelos import Factura
    from servidor.servicios import agente, pagos
    h = entrar(cliente, "carlos.rivera@brisamar.example")
    d = cliente.get("/api/simulador/escenarios/monto_inflado?periodo=2026-11", headers=h).json()
    f = cliente.post("/api/simulador/factura", json=d, headers=h).json()
    cliente.post(f"/api/facturas/{f['id']}/aprobar", json={"comentario": "Trabajo extra aprobado."}, headers=h)
    with SesionBD() as bd:  # alguien altera el monto directamente en la base de datos después de aprobar
        fac = bd.get(Factura, f["id"])
        fac.monto_usd = fac.monto_usd + 1
        with pytest.raises(ValueError, match="ya no coincide"):
            pagos.crear_y_ejecutar(bd, fac, agente.reglas_vigentes(bd), "prueba", intento=9)
        bd.rollback()


def test_un_solo_pago_vivo_por_factura(cliente):
    from sqlalchemy.exc import IntegrityError
    from servidor.db import SesionBD
    from servidor.modelos import Pago
    with SesionBD() as bd:
        p = bd.query(Pago).filter(Pago.estado == "liquidado").first()
        copia = Pago(**{c.name: getattr(p, c.name) for c in Pago.__table__.columns if c.name not in ("id", "clave_idempotencia")},
                     id="PAG-COPIA", clave_idempotencia="otra-clave")
        bd.add(copia)
        with pytest.raises(IntegrityError):
            bd.commit()


def test_auditoria_detecta_alteraciones(cliente):
    from servidor.db import SesionBD
    from servidor.modelos import EventoAuditoria
    from servidor.servicios import auditoria
    with SesionBD() as bd:
        assert auditoria.verificar(bd)["ok"]
        ev = bd.get(EventoAuditoria, 3)
        original = ev.resumen
        ev.resumen = original + " (editado)"
        bd.flush()
        r = auditoria.verificar(bd)
        assert not r["ok"] and r["evento_alterado"] == 3
        bd.rollback()


def test_libro_mayor_cuadrado(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    w = cliente.get("/api/wallet", headers=h).json()
    assert w["libro"]["ok"] is True


def test_simulador_anio_sin_pagos_indebidos(cliente):
    h = entrar(cliente, "carlos.rivera@brisamar.example")
    for semilla in (1, 7, 30):
        r = cliente.post("/api/simulador/anio", json={"meses": 12, "trampas_pct": 40, "semilla": semilla}, headers=h).json()
        assert r["pagos_indebidos"] == 0 and r["trampas_pagadas"] == 0 and r["total"] > 100


def test_carga_rechaza_tipos_falsos(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    h.pop("Content-Type", None)
    r = cliente.post("/api/facturas/cargar", files={"archivo": ("factura.pdf", b"MZ\x90\x00 ejecutable", "application/pdf")}, headers=h)
    assert r.status_code == 415
    r = cliente.post("/api/facturas/cargar", files={"archivo": ("x.exe", b"MZ", "application/octet-stream")}, headers=h)
    assert r.status_code == 415


def test_xml_malicioso_por_la_api(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    datos = (RAIZ / "data" / "sorpresa" / "S03_proveedor-desconocido_FX-001.xml").read_bytes()
    r = cliente.post("/api/facturas/cargar", files={"archivo": ("ataque.xml", datos, "application/xml")}, headers=h)
    assert r.status_code == 200
    f = r.json()
    assert f["estado"] == "pendiente" and f["regla"] == "R01" and "seguridad" in f["motivo"].lower()


def test_politica_de_contrasenas():
    from servidor.seguridad.contrasenas import problemas_politica
    from servidor.servicios.semilla import CONTRASENA_DEMO, USUARIOS_DEMO
    assert problemas_politica("corta-2026") != []                      # menos de 15 caracteres
    assert problemas_politica("password1234567") != []                 # contraseña común
    assert problemas_politica("mariana.torres-2026-ok", "mariana.torres@brisamar.example") != []  # contiene el usuario
    assert problemas_politica("una frase larga sin reglas raras") == []  # sin reglas de composición
    assert all(problemas_politica(CONTRASENA_DEMO, c) == [] for c, *_ in USUARIOS_DEMO)


def test_personas_invitacion_registro_y_roles(cliente):
    h = entrar(cliente, "tomas.herrera@brisamar.example")            # administración (CTO)
    assert cliente.get("/api/personas", headers=h).status_code == 200
    r = cliente.post("/api/personas/invitar", headers=h, json={
        "correo": "prueba.alta@brisamar.example", "nombre": "Prueba Alta", "cargo": "Analista", "rol": "cto"})
    assert r.status_code == 200
    codigo = r.json()["codigo"]
    # quien no es administración no invita ni ve la lista
    h2 = entrar(cliente, "carlos.rivera@brisamar.example")
    assert cliente.post("/api/personas/invitar", headers=h2, json={
        "correo": "x@brisamar.example", "nombre": "X Y", "cargo": "", "rol": "cto"}).status_code == 403
    assert cliente.get("/api/personas", headers=h2).status_code == 403
    LIMITADOR.reiniciar()
    cliente.post("/api/auth/logout", headers=ORIGEN)
    # el registro necesita el código correcto y una contraseña que cumpla la política
    assert cliente.post("/api/personas/registro", headers=ORIGEN, json={
        "correo": "prueba.alta@brisamar.example", "codigo": "KAUX-0000-0000",
        "contrasena": "una frase larga y propia"}).status_code == 409
    assert cliente.post("/api/personas/registro", headers=ORIGEN, json={
        "correo": "prueba.alta@brisamar.example", "codigo": codigo, "contrasena": "corta"}).status_code == 422
    r = cliente.post("/api/personas/registro", headers=ORIGEN, json={
        "correo": "prueba.alta@brisamar.example", "codigo": codigo, "contrasena": "una frase larga y propia"})
    assert r.status_code == 200 and r.json()["rol"] == "cto"      # el rol lo decide la invitación
    assert cliente.post("/api/personas/registro", headers=ORIGEN, json={      # el código sirve una sola vez
        "correo": "prueba.alta@brisamar.example", "codigo": codigo, "contrasena": "otra frase larga aun"}).status_code == 409
    # la persona nueva entra con su rol y puede cambiar su propia contraseña
    nh = entrar(cliente, "prueba.alta@brisamar.example", "una frase larga y propia")
    assert cliente.post("/api/personas/mi-contrasena", headers=nh, json={
        "actual": "una frase larga y propia", "nueva": "mi nueva frase de acceso"}).status_code == 200
    # administración la desactiva y deja de poder entrar
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    uid = [u["id"] for u in cliente.get("/api/personas", headers=h).json()["usuarios"]
           if u["correo"] == "prueba.alta@brisamar.example"][0]
    assert cliente.put(f"/api/personas/{uid}/rol", headers=h, json={"rol": "cfo"}).status_code == 200
    assert cliente.put(f"/api/personas/{uid}/activo", headers=h, json={"activo": False}).json()["activo"] is False
    LIMITADOR.reiniciar()
    assert cliente.post("/api/auth/login", headers=ORIGEN, json={
        "correo": "prueba.alta@brisamar.example", "contrasena": "mi nueva frase de acceso"}).status_code == 401
    # siempre debe quedar alguien en administración
    h = entrar(cliente, "tomas.herrera@brisamar.example")
    yo = [u for u in cliente.get("/api/personas", headers=h).json()["usuarios"] if u["rol"] == "cto"]
    assert len(yo) == 1
    assert cliente.put(f"/api/personas/{yo[0]['id']}/rol", headers=h, json={"rol": "ceo"}).status_code == 409


def test_lector_local_sin_ia(cliente):
    """El OCR es opcional: si Tesseract no está, Kauta sigue funcionando con los otros lectores."""
    from kauta import ocr
    if not ocr.disponible():
        pytest.skip("Tesseract con el idioma spa no está instalado")
    ruta = RAIZ / "data" / "facturas" / "F09_soporte-nexo_SN-3307.pdf"
    campos = ocr.leer(ruta.name, ruta.read_bytes())
    assert campos and campos["beneficiario"]["id_fiscal"].replace(".", "").replace(" ", "") == "NIT900618442-0"
    assert campos["numero_factura"] == "SN-3307" and campos["monto"] == 2450.0 and campos["moneda"] == "USD"
    assert campos["cuenta_destino"] == "6618" and campos["tipo_documento"] == "factura"
    assert all(campos["confianza"][c] >= 0.8 for c in ("beneficiario", "numero_factura", "moneda", "monto"))
    # la foto borrosa es justo la que no se debe adivinar: sin total legible y con confianza en cero
    borrosa = RAIZ / "data" / "facturas" / "F13_ana-rios_foto-factura.jpg"
    campos = ocr.leer(borrosa.name, borrosa.read_bytes())
    assert campos["monto"] is None and campos["confianza"]["monto"] == 0.0
    assert "sin_total_legible" in campos["alertas"]


# ---------------------------------------------------------------------------
# Demo sin login: entrar como persona (plan-eng-review D1, D2)
# ---------------------------------------------------------------------------
def persona(c, correo):
    r = c.post("/api/auth/persona", json={"correo": correo}, headers=ORIGEN)
    assert r.status_code == 200, r.text
    return {**ORIGEN, "X-CSRF-Token": r.json()["usuario"]["csrf"]}


def test_persona_sin_contrasena_y_sin_bloqueo(cliente):
    LIMITADOR.reiniciar()
    for i in range(30):  # cambiar de persona muchas veces no choca con el límite del login (10 por minuto)
        correo = ["carlos.rivera@brisamar.example", "mariana.torres@brisamar.example", "tomas.herrera@brisamar.example"][i % 3]
        persona(cliente, correo)
    r = cliente.get("/api/auth/yo")
    assert r.status_code == 200 and r.json()["usuario"]["rol"] == "cto"
    assert cliente.post("/api/auth/persona", json={"correo": "nadie@brisamar.example"}, headers=ORIGEN).status_code == 404


def test_persona_mantiene_permisos_y_csrf(cliente):
    h = persona(cliente, "tomas.herrera@brisamar.example")  # el CTO no firma
    assert cliente.post("/api/facturas/F09/aprobar", json={"comentario": "intento"}, headers=h).status_code == 403
    assert cliente.post("/api/facturas/F09/rechazar", json={"comentario": "x"}, headers=ORIGEN).status_code == 403  # sin CSRF


# ---------------------------------------------------------------------------
# Control 2: un cambio de reglas nunca paga solo ni baja firmas (plan-eng-review, sección 6)
# ---------------------------------------------------------------------------
def _cambiar_reglas(c, h, **cambios):
    vigente = c.get("/api/reglas", headers=h).json()["vigente"]
    cuerpo = {k: vigente[k] for k in ("presupuesto_periodo_usd", "umbral_aprobacion_usd", "limite_maximo_pago_usd",
                                      "limite_beneficiario_periodo_usd", "tolerancia_contrato_pct", "confianza_minima",
                                      "monedas_permitidas")} | cambios | {"motivo": "Prueba del control de reevaluación."}
    r = c.put("/api/reglas", json=cuerpo, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_cambio_de_reglas_no_paga_solo_ni_baja_firmas(cliente):
    h = persona(cliente, "carlos.rivera@brisamar.example")
    antes = {f["id"]: f for f in cliente.get("/api/facturas", headers=h).json()}
    assert antes["F10"]["estado"] == "pendiente" and antes["F10"]["aprobaciones_requeridas"] == 2
    _cambiar_reglas(cliente, h, umbral_aprobacion_usd=5000, presupuesto_periodo_usd=40000)
    despues = {f["id"]: f for f in cliente.get("/api/facturas", headers=h).json()}
    assert despues["F10"]["estado"] == "pendiente" and despues["F10"]["aprobaciones_requeridas"] == 2
    # nada que estaba frenado o pendiente pasó a pagado por el cambio
    assert not [i for i, f in antes.items() if f["estado"] in ("frenada", "pendiente") and despues[i]["estado"] == "pagada"]


def test_quien_cambia_reglas_no_es_firma_unica(cliente):
    from servidor.db import SesionBD
    from servidor.modelos import Factura
    with SesionBD() as bd:
        f = bd.query(Factura).filter(Factura.excluir_firmante == "carlos.rivera@brisamar.example",
                                     Factura.aprobaciones_requeridas == 1, Factura.estado == "pendiente").first()
        assert f is not None, "el cambio de presupuesto debe dejar al menos una factura pendiente de 1 firma"
        fid = f.id
    h = persona(cliente, "carlos.rivera@brisamar.example")
    r = cliente.post(f"/api/facturas/{fid}/aprobar", json={"comentario": "Lo cambié yo y lo apruebo."}, headers=h)
    assert r.status_code == 409 and "otra persona" in r.json()["detail"]
    h2 = persona(cliente, "mariana.torres@brisamar.example")
    r = cliente.post(f"/api/facturas/{fid}/aprobar", json={"comentario": "Revisado por otra persona."}, headers=h2)
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Libro de costos sobre la base sembrada (plan-eng-review D10, D14 e invariante)
# ---------------------------------------------------------------------------
def test_costos_idempotentes_y_conflicto_auditado(cliente):
    from servidor.db import SesionBD
    from servidor.modelos import EventoAuditoria, EventoCosto, Factura, Pago
    from servidor.servicios import costos
    with SesionBD() as bd:
        p = bd.query(Pago).filter(Pago.estado == "liquidado").first()
        f = bd.get(Factura, p.factura_id)
        antes = bd.query(EventoCosto).count()
        costos.registrar_pago(bd, f, p)                       # repetir el mismo pago no vuelve a cobrar
        assert bd.query(EventoCosto).count() == antes
        p.comision_usd = p.comision_usd + 1                   # misma clave, otro importe: no se sobrescribe
        costos.registrar_pago(bd, f, p)
        ev = bd.query(EventoCosto).filter(EventoCosto.fuente == "pago_comision",
                                          EventoCosto.origen_id == f"pago:{p.clave_idempotencia}").one()
        assert int(ev.importe_nano_usd) != costos.a_nano(p.comision_usd)
        assert bd.query(EventoAuditoria).filter(EventoAuditoria.tipo == "costo.conflicto").count() >= 1
        bd.rollback()


def test_costos_no_se_confirman_aparte(cliente):
    from servidor.db import SesionBD
    from servidor.modelos import EventoCosto, Factura
    from servidor.servicios import costos
    with SesionBD() as bd:
        f = bd.get(Factura, "F01")
        try:
            with bd.begin_nested():
                costos.registrar_lectura(bd, f, 0.85, n_intento=99)
                raise RuntimeError("falla entre la acción y su confirmación")
        except RuntimeError:
            pass
        bd.commit()
        n = bd.query(EventoCosto).filter(EventoCosto.factura_id == "F01", EventoCosto.fuente.like("lectura_%")).count()
        assert n == 1  # solo la lectura original; la del intento revertido no quedó


def test_invariante_y_tesis_de_la_ia(cliente):
    from decimal import Decimal
    from servidor.db import SesionBD
    from servidor.modelos import EventoCosto
    from servidor.servicios import agente, costos, metricas
    h = persona(cliente, "carlos.rivera@brisamar.example")
    rend = cliente.get("/api/rendimiento", headers=h).json()
    assert [t["id"] for t in rend["tarjetas"]] == ["costo_por_factura_resuelta", "costo_de_pagar", "leido_sin_ia", "cobertura"]
    with SesionBD() as bd:
        per = agente.reglas_vigentes(bd)["periodo_actual"]
        lib = metricas.Libro(bd, per)
        suma = sum((lib.recibo(f)["total_usd"] for f in lib.finales()), Decimal(0))
        assert suma == lib.costo_por_factura_resuelta()["numerador_usd"]
        por = {}
        for e in bd.query(EventoCosto).all():
            por[e.fuente] = por.get(e.fuente, Decimal(0)) + (costos.a_usd(e.importe_nano_usd) or 0)
        assert bd.query(EventoCosto).filter(EventoCosto.fuente == "lectura_ia").count() >= 1  # F13: la prueba no pasa en vacío
        ia_x10 = por["lectura_ia"] * 10
        assert ia_x10 < por["revision_humana"] and ia_x10 < por["pago_cambio"]
    r = cliente.get("/api/facturas/F13/recibo", headers=h).json()
    assert any("IA" in l["titulo"] for l in r["lineas"])
    lente = cliente.get("/api/resumen", headers=h).json()["lente"]
    assert len(lente["tarjetas"]) <= 4 and lente["pregunta"]


def test_restablecer_es_determinista(cliente):
    h = persona(cliente, "tomas.herrera@brisamar.example")
    vistas = []
    for _ in range(2):
        assert cliente.post("/api/demo/restablecer", json={"con_set": True}, headers=h).status_code == 200
        h = persona(cliente, "tomas.herrera@brisamar.example")
        r = cliente.get("/api/rendimiento", headers=h).json()
        r.pop("calculado_en")
        vistas.append(r)
    assert vistas[0] == vistas[1]
