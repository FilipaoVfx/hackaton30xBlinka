"""Pruebas del libro de costos y sus métricas (plan-eng-review: prueba de aceptación, cobertura y cierre de mes)."""
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as N

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from servidor.servicios.costos import a_nano  # noqa: E402
from servidor.servicios.metricas import Libro  # noqa: E402

AHORA = datetime(2026, 10, 17, 20, 0)  # octubre sigue abierto


def factura(fid, estado, periodo="2026-10", resuelta=datetime(2026, 10, 10)):
    return N(id=fid, estado=estado, periodo=periodo, resuelta_en=resuelta if estado in ("pagada", "frenada", "rechazada") else None,
             monto_usd=Decimal("100"), motivo="", extraccion={})


def ev(fid, fuente, usd, origen=None, periodo="2026-10"):
    return N(factura_id=fid, fuente=fuente, origen_id=origen or f"{fuente}:{fid}:{usd}", periodo=periodo,
             importe_nano_usd=None if usd is None else a_nano(usd), detalle="", minutos=None)


def escenario():
    """8 pagadas y 2 frenadas con USD 100 conocidos (lectura 20, revisión 30, pago 40, infraestructura 10) y una pendiente."""
    fs = [factura(f"P{i}", "pagada") for i in range(8)] + [factura("X1", "frenada"), factura("X2", "frenada")]
    eventos = []
    for f in fs:
        eventos += [ev(f.id, "lectura_texto", 2), ev(f.id, "revision_humana", 3)]
    for i, f in enumerate(fs[:8]):
        if i == 0:  # una orden fallida de USD 0,50 y el reintento: la comisión de las dos cuenta
            eventos += [ev(f.id, "pago_comision", "0.50", "pago:fallida"), ev(f.id, "pago_comision", "4.50", "pago:reintento")]
        else:
            eventos.append(ev(f.id, "pago_comision", 5))
    eventos.append(N(factura_id=None, fuente="infraestructura", origen_id="infra:2026-10", periodo="2026-10",
                     importe_nano_usd=a_nano(10), detalle="", minutos=None))
    pendiente = factura("A1", "pendiente")
    eventos += [ev("A1", "lectura_texto", 3), ev("A1", "revision_humana", 4)]
    return fs + [pendiente], eventos


def test_aceptacion_costo_por_factura_resuelta_y_de_pagar():
    fs, eventos = escenario()
    lib = Libro.desde(fs, eventos, [], [], AHORA)
    cpr = lib.costo_por_factura_resuelta()
    assert cpr["denominador"] == 10 and cpr["numerador_usd"] == Decimal(100)
    assert cpr["valor_usd"] == Decimal(10)
    assert lib.costo_de_pagar()["valor_usd"] == Decimal(5)
    assert cpr["en_curso_usd"] == Decimal(7)  # la pendiente queda aparte, no en el numerador


def test_aceptacion_sin_la_pendiente_da_lo_mismo():
    fs, eventos = escenario()
    fs = [f for f in fs if f.id != "A1"]
    eventos = [e for e in eventos if e.factura_id != "A1"]
    lib = Libro.desde(fs, eventos, [], [], AHORA)
    assert lib.costo_por_factura_resuelta()["valor_usd"] == Decimal(10)
    assert lib.costo_de_pagar()["valor_usd"] == Decimal(5)


def test_invariante_recibos_suman_el_numerador():
    fs, eventos = escenario()
    lib = Libro.desde(fs, eventos, [], [], AHORA)
    suma = sum((lib.recibo(f)["total_usd"] for f in lib.finales()), Decimal(0))
    assert suma == lib.costo_por_factura_resuelta()["numerador_usd"]


def test_cobertura_baja_si_falta_una_comision_aunque_haya_lecturas_de_mas():
    f = factura("F", "pagada")
    eventos = [ev("F", "lectura_texto", 0), ev("F", "lectura_ocr", "0.0005"), ev("F", "lectura_ia", "0.027"),
               N(factura_id=None, fuente="infraestructura", origen_id="infra:2026-10", periodo="2026-10",
                 importe_nano_usd=a_nano(30), detalle="", minutos=None)]
    pago = N(clave_idempotencia="pago:F:1", moneda_destino="USD")  # su comisión nunca se registró
    cob = Libro.desde([f], eventos, [pago], [], AHORA).cobertura()
    assert cob["esperadas"] == 3 and cob["conocidas"] == 2 and cob["pct"] < 100


def test_costo_desconocido_no_vale_cero():
    f = factura("F", "pagada")
    eventos = [ev("F", "lectura_ia", None)]
    lib = Libro.desde([f], eventos, [], [], AHORA)
    assert lib.cobertura()["conocidas"] == 0
    assert lib.recibo(f)["total_completo"] is False


def test_mes_cerrado_no_cambia_los_recibos_ya_emitidos():
    ahora = datetime(2026, 11, 3, 12, 0)  # septiembre ya cerró
    a = factura("S1", "pagada", "2026-09", resuelta=datetime(2026, 9, 20))
    b = factura("S2", "pagada", "2026-09", resuelta=datetime(2026, 9, 25))
    infra = N(factura_id=None, fuente="infraestructura", origen_id="infra:2026-09", periodo="2026-09",
              importe_nano_usd=a_nano(30), detalle="", minutos=None)
    antes = Libro.desde([a, b], [infra], [], [], ahora).recibo(a)["total_usd"]
    tardia = factura("S3", "pagada", "2026-09", resuelta=datetime(2026, 11, 2))  # se resolvió después del cierre
    lib = Libro.desde([a, b, tardia], [infra], [], [], ahora)
    assert lib.recibo(a)["total_usd"] == antes == Decimal(15)
    nota = [l for l in lib.recibo(tardia)["lineas"] if l["fuente"] == "infraestructura"][0]
    assert nota["importe_usd"] == 0 and "mes cerrado" in nota["detalle"]
