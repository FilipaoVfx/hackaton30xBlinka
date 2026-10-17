"""
Libro de costos: escribe un evento por cada costo que causa una factura.

    lectura ──► lectura_xml | lectura_texto | lectura_ocr (+ lectura_ia si el OCR no alcanza)
    firma o respuesta humana ──► revision_humana
    pago ──► pago_comision (+ pago_cambio si la moneda de destino no es USD)
    primer documento del mes ──► infraestructura (un asiento por mes, sin factura)

Reglas (plan-eng-review D10): cada evento se agrega con la sesión de quien llama y se confirma en el
mismo commit que la acción que lo causa; aquí nunca se hace commit. La clave (fuente, origen_id) hace
que repetir un evento no vuelva a cobrar; si llega la misma clave con otro importe, no se sobrescribe:
queda un evento de auditoría «costo.conflicto». Las tarifas son simuladas y declaradas en data/tarifas.json.
"""
from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import RAIZ
from ..modelos import Aprobacion, EventoCosto, Factura, Pago
from . import BLOQUEO, auditoria

NANO = Decimal(1_000_000_000)
IMAGENES = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")


@lru_cache(maxsize=1)
def tarifas() -> dict[str, Any]:
    return json.loads((RAIZ / "data" / "tarifas.json").read_text(encoding="utf-8"))


def a_nano(usd: Decimal | float | int) -> int:
    return int((Decimal(str(usd)) * NANO).quantize(Decimal(1), ROUND_HALF_UP))


def a_usd(nano: int | Decimal | None) -> Decimal | None:
    return None if nano is None else Decimal(int(nano)) / NANO


def _registrar(bd: Session, *, fuente: str, origen_id: str, periodo: str, factura_id: str | None,
               importe_usd: Decimal | None, **extra: Any) -> EventoCosto | None:
    nano = None if importe_usd is None else a_nano(importe_usd)
    with BLOQUEO:
        previo = bd.execute(select(EventoCosto).where(EventoCosto.fuente == fuente,
                                                      EventoCosto.origen_id == origen_id)).scalar_one_or_none()
        if previo:
            mismo = (previo.importe_nano_usd is None and nano is None) or (
                previo.importe_nano_usd is not None and nano is not None and int(previo.importe_nano_usd) == nano)
            if not mismo or previo.tarifa_version != tarifas()["version"]:
                auditoria.registrar(bd, "costo.conflicto", "Libro de costos", "costo", f"{fuente}:{origen_id}",
                                    f"Se ignoró un costo repetido con otro importe para {fuente} ({origen_id}); "
                                    "el libro conserva el primero.", {"existente": str(previo.importe_nano_usd), "nuevo": str(nano)})
            return previo
        ev = EventoCosto(fuente=fuente, origen_id=origen_id, periodo=periodo, factura_id=factura_id,
                         importe_nano_usd=nano, tarifa_version=tarifas()["version"], **extra)
        bd.add(ev)
        bd.flush()
        return ev


def asegurar_infraestructura(bd: Session, periodo: str) -> None:
    t = tarifas()["infraestructura"]
    _registrar(bd, fuente="infraestructura", origen_id=f"infra:{periodo}", periodo=periodo, factura_id=None,
               importe_usd=Decimal(str(t["usd_por_mes"])), detalle=f"Servidor y base de la demo, {periodo} (declarado)")


def camino_lectura(f: Factura, confianza_minima: float) -> list[str]:
    """La cascada que siguió la factura: XML fiscal → texto → OCR → IA (solo si el OCR no alcanzó)."""
    archivo = (f.archivo or "").lower()
    if f.metodo_lectura == "xml_fiscal" or archivo.endswith(".xml") or archivo.endswith(".zip"):
        return ["lectura_xml"]
    if archivo.endswith(IMAGENES):
        conf = (f.extraccion or {}).get("confianza") or {}
        criticos = ("beneficiario", "numero_factura", "moneda", "monto")
        if any(float(conf.get(c, 0) or 0) < confianza_minima for c in criticos):
            return ["lectura_ocr", "lectura_ia"]
        return ["lectura_ocr"]
    return ["lectura_texto"]


def registrar_lectura(bd: Session, f: Factura, confianza_minima: float, n_intento: int = 1) -> None:
    t = tarifas()
    intento = hashlib.sha256(f"{f.id}|{f.hash_documento}|lector-v1|{n_intento}".encode()).hexdigest()[:40]
    paginas = 1
    for fuente in camino_lectura(f, confianza_minima):
        origen = f"lectura:{intento}"
        if fuente == "lectura_xml":
            _registrar(bd, fuente=fuente, origen_id=origen, periodo=f.periodo, factura_id=f.id,
                       importe_usd=Decimal(str(t["xml"]["usd_por_documento"])), latencia_ms=t["xml"]["latencia_ms"],
                       paginas=paginas, detalle="XML fiscal, exacto y sin IA")
        elif fuente == "lectura_texto":
            _registrar(bd, fuente=fuente, origen_id=origen, periodo=f.periodo, factura_id=f.id,
                       importe_usd=Decimal(str(t["texto"]["usd_por_documento"])), latencia_ms=t["texto"]["latencia_ms"],
                       paginas=paginas, detalle="Texto del documento, sin IA")
        elif fuente == "lectura_ocr":
            _registrar(bd, fuente=fuente, origen_id=origen, periodo=f.periodo, factura_id=f.id,
                       importe_usd=Decimal(str(t["ocr"]["usd_por_pagina"])) * paginas,
                       latencia_ms=t["ocr"]["latencia_ms_por_pagina"] * paginas, paginas=paginas,
                       detalle="OCR local (Tesseract), sin IA")
        else:
            ia = t["ia"]
            entrada, salida = ia["tokens_entrada_por_pagina"] * paginas, ia["tokens_salida_por_pagina"] * paginas
            importe = (Decimal(entrada) * Decimal(str(ia["usd_por_millon_entrada"]))
                       + Decimal(salida) * Decimal(str(ia["usd_por_millon_salida"]))) / Decimal(1_000_000)
            _registrar(bd, fuente=fuente, origen_id=origen, periodo=f.periodo, factura_id=f.id, importe_usd=importe,
                       tokens_entrada=entrada, tokens_cache=0, tokens_salida=salida,
                       latencia_ms=ia["latencia_ms_por_pagina"] * paginas, paginas=paginas,
                       detalle="IA (lector simulado): el OCR no alcanzó la confianza mínima")
    asegurar_infraestructura(bd, f.periodo)


def registrar_revision(bd: Session, f: Factura, a: Aprobacion, correo: str) -> None:
    t = tarifas()["revision_humana"]
    minutos = t["minutos_firma"] if (a.accion == "aprobar" and a.nivel > 1) else t["minutos_respuesta"]
    importe = Decimal(str(t["usd_por_hora"])) * Decimal(minutos) / Decimal(60)
    accion = "firma" if a.nivel > 1 else ("rechazo" if a.accion == "rechazar" else "respuesta y firma")
    _registrar(bd, fuente="revision_humana", origen_id=f"aprobacion:{a.id}", periodo=f.periodo, factura_id=f.id,
               importe_usd=importe, persona=correo, minutos=minutos,
               detalle=f"{a.usuario_nombre}: {accion}, {minutos} min (estimado)")


def registrar_pago(bd: Session, f: Factura, p: Pago) -> None:
    _registrar(bd, fuente="pago_comision", origen_id=f"pago:{p.clave_idempotencia}", periodo=f.periodo, factura_id=f.id,
               importe_usd=Decimal(p.comision_usd), detalle=f"Comisión del riel {p.riel} ({p.id})")
    if p.moneda_destino != "USD":
        _registrar(bd, fuente="pago_cambio", origen_id=f"pago:{p.clave_idempotencia}", periodo=f.periodo, factura_id=f.id,
                   importe_usd=Decimal(p.costo_fx_usd), detalle=f"Cambio USD→{p.moneda_destino} ({p.id})")
