"""
Métricas de Kauta: una sola fuente para el Resumen, el Recibo de cada factura y Rendimiento y costos.

Catálogo (cada cifra declara numerador, denominador y cobertura):

    autonomia_set_pct / autonomia_pct   primera decisión pagar o frenar sin persona / facturas (set o todas)
    dinero_protegido_usd                monto USD de las facturas frenadas y rechazadas
    pagos_fuera_de_reglas               pagos que violan una regla sin la aprobación que corresponde
    costo_por_factura_resuelta          costos de las facturas finales (+ su parte de infraestructura) / facturas finales
    costo_de_pagar_una_factura          comisión + cambio de todas sus órdenes / facturas pagadas
    leido_sin_ia_pct                    facturas sin ninguna lectura por IA / facturas leídas (unidad: la factura)
    cobertura_pct                       casillas con importe conocido / casillas esperadas (tope 100 %)

Estados finales: pagada, frenada, rechazada. No finales: pendiente, devuelta (sus costos van aparte, «en curso»).
Los costos de una factura pertenecen al mes en que se recibió (su periodo). La infraestructura del mes se reparte
en partes iguales entre las facturas finales de ese mes; el mes cierra al terminar su último día (Bogotá) y una
factura que se resuelve después del cierre no recibe parte. No hay cortes históricos: todo es «ahora».

Invariante: la suma de los recibos de las facturas finales es el numerador del costo por factura resuelta.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import RAIZ
from ..modelos import ESTADOS_FINALES, Aprobacion, EventoCosto, Factura, Pago
from . import agente
from .costos import a_usd

LECTURAS = ("lectura_xml", "lectura_texto", "lectura_ocr", "lectura_ia")
GRUPO = {"lectura_xml": "lectura", "lectura_texto": "lectura", "lectura_ocr": "lectura", "lectura_ia": "lectura",
         "revision_humana": "revision", "pago_comision": "pago", "pago_cambio": "pago", "infraestructura": "infraestructura"}
BOGOTA = timezone(timedelta(hours=-5))
CENT = Decimal("0.01")


# ---------------------------------------------------------------------------
# Métricas del reto (definiciones de siempre, plan-eng-review D4)
# ---------------------------------------------------------------------------
def esperado_set() -> dict[str, dict[str, str]]:
    ruta = RAIZ / "data" / "esperado.csv"
    return {r["factura_id"]: r for r in csv.DictReader(open(ruta, encoding="utf-8"))} if ruta.exists() else {}


def base(bd: Session) -> dict[str, Any]:
    fs = bd.execute(select(Factura)).scalars().all()
    tot = len(fs)
    cuenta = lambda e: sum(1 for f in fs if f.estado == e)
    autonomas = sum(1 for f in fs if f.decision_inicial in ("pagar", "frenar"))
    indebidos = 0
    for f in fs:
        if f.estado != "pagada":
            continue
        aprobadas = [a for a in f.aprobaciones if a.accion == "aprobar"]
        fallas = [r for r in f.reglas if r["estado"] == "falla"]
        if not aprobadas and fallas:
            indebidos += 1
        if aprobadas and any(r["efecto"] == "frenar" for r in fallas):
            indebidos += 1
        if aprobadas and len(aprobadas) < f.aprobaciones_requeridas:
            indebidos += 1
    esperado = esperado_set()
    del_set = [f for f in fs if f.id in esperado]
    aciertos = sum(1 for f in del_set if f.decision_inicial == esperado[f.id]["decision_esperada"]
                   and agente.regla_principal(f.motivo_inicial) == esperado[f.id]["regla_principal"])
    protegido = sum((float(f.monto_usd or 0) for f in fs if f.estado in ("frenada", "rechazada")), 0.0)
    autonomas_set = sum(1 for f in del_set if f.decision_inicial in ("pagar", "frenar"))
    trampas = [f for f in del_set if esperado[f.id]["tipo_caso"] == "trampa"]
    return {
        "total": tot, "pagadas": cuenta("pagada"), "frenadas": cuenta("frenada"), "pendientes": cuenta("pendiente"),
        "rechazadas": cuenta("rechazada"), "devueltas": cuenta("devuelta"),
        "autonomia_pct": round(100 * autonomas / tot, 1) if tot else 0.0,
        "pagos_fuera_de_reglas": indebidos,
        "explicadas_pct": round(100 * sum(1 for f in fs if f.motivo and f.reglas) / tot, 1) if tot else 0.0,
        "set_aciertos": aciertos, "set_total": len(del_set),
        "autonomia_set_pct": round(100 * autonomas_set / len(del_set), 1) if del_set else 0.0,
        "trampas_detenidas": sum(1 for f in trampas if f.decision_inicial != "pagar"), "trampas_total": len(trampas),
        "dinero_protegido_usd": round(protegido, 2),
        "lectura_xml": sum(1 for f in fs if f.metodo_lectura == "xml_fiscal"),
    }


# ---------------------------------------------------------------------------
# Libro de costos
# ---------------------------------------------------------------------------
def cierre_de(periodo: str) -> datetime:
    """Primer instante del mes siguiente en Bogotá, expresado en UTC sin zona (como guarda la base)."""
    anio, mes = (int(x) for x in periodo.split("-"))
    sig = datetime(anio + (mes == 12), 1 if mes == 12 else mes + 1, 1, tzinfo=BOGOTA)
    return sig.astimezone(timezone.utc).replace(tzinfo=None)


def mes_cerrado(periodo: str, ahora: datetime | None = None) -> bool:
    ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
    return ahora >= cierre_de(periodo)


def _cuenta_en_reparto(f: Factura, ahora: datetime | None = None) -> bool:
    """Una factura final recibe parte de la infraestructura de su mes, salvo si se resolvió después del cierre."""
    if f.estado not in ESTADOS_FINALES:
        return False
    if mes_cerrado(f.periodo, ahora) and f.resuelta_en and f.resuelta_en >= cierre_de(f.periodo):
        return False
    return True


class Libro:
    """Vista en memoria del libro para un periodo (o para todos). Todas las cifras de costo salen de aquí."""

    def __init__(self, bd: Session, periodo: str | None = None, ahora: datetime | None = None):
        q = select(Factura)
        if periodo:
            q = q.where(Factura.periodo == periodo)
        facturas = bd.execute(q).scalars().all()
        qe = select(EventoCosto)
        if periodo:
            qe = qe.where(EventoCosto.periodo == periodo)
        ids = [f.id for f in facturas]
        pagos = bd.execute(select(Pago).where(Pago.factura_id.in_(ids))).scalars().all() if ids else []
        aprob = bd.execute(select(Aprobacion).where(Aprobacion.factura_id.in_(ids))).scalars().all() if ids else []
        self._armar(facturas, bd.execute(qe).scalars().all(), pagos, aprob, ahora)

    @classmethod
    def desde(cls, facturas: list, eventos: list, pagos: list, aprobaciones: list, ahora: datetime | None = None) -> "Libro":
        """Construye el libro con datos ya cargados (lo usan las pruebas de aceptación)."""
        lib = cls.__new__(cls)
        lib._armar(facturas, eventos, pagos, aprobaciones, ahora)
        return lib

    def _armar(self, facturas: list, eventos: list, pagos: list, aprobaciones: list, ahora: datetime | None) -> None:
        self.ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
        self.facturas = {f.id: f for f in facturas}
        self.eventos = list(eventos)
        self.por_factura: dict[str, list[EventoCosto]] = defaultdict(list)
        self.infra: dict[str, EventoCosto] = {}
        for e in self.eventos:
            if e.fuente == "infraestructura":
                self.infra[e.periodo] = e
            elif e.factura_id:
                self.por_factura[e.factura_id].append(e)
        self.pagos = list(pagos)
        self.aprobaciones = list(aprobaciones)
        self.reparto: dict[str, int] = defaultdict(int)
        for f in self.facturas.values():
            if _cuenta_en_reparto(f, self.ahora):
                self.reparto[f.periodo] += 1

    # -------- partes
    def parte_infra(self, f: Factura) -> tuple[Decimal | None, str]:
        e = self.infra.get(f.periodo)
        if e is None:
            return None, "sin asiento de infraestructura"
        if f.estado not in ESTADOS_FINALES:
            return Decimal(0), "aún no resuelta"
        if not _cuenta_en_reparto(f, self.ahora):
            return Decimal(0), "sin infraestructura: mes cerrado"
        total = a_usd(e.importe_nano_usd)
        if total is None:
            return None, "infraestructura desconocida"
        n = self.reparto[f.periodo] or 1
        estado = "cerrado" if mes_cerrado(f.periodo, self.ahora) else "provisional"
        return total / n, f"1/{n} de {total.quantize(CENT)} USD del mes ({estado})"

    def costos_de(self, f: Factura) -> dict[str, Decimal | None]:
        """Importe por fuente de una factura; None si alguna parte de esa fuente es desconocida."""
        out: dict[str, Decimal | None] = {}
        for e in self.por_factura.get(f.id, []):
            v = a_usd(e.importe_nano_usd)
            if e.fuente in out and out[e.fuente] is None:
                continue
            out[e.fuente] = None if v is None else (out.get(e.fuente) or Decimal(0)) + v
        return out

    def total_de(self, f: Factura, con_infra: bool = True) -> Decimal:
        total = sum((v for v in self.costos_de(f).values() if v is not None), Decimal(0))
        if con_infra:
            parte, _ = self.parte_infra(f)
            total += parte or Decimal(0)
        return total

    # -------- métricas
    def finales(self) -> list[Factura]:
        return [f for f in self.facturas.values() if f.estado in ESTADOS_FINALES]

    def por_grupo(self, facturas: list[Factura]) -> dict[str, Decimal]:
        g = {"lectura": Decimal(0), "revision": Decimal(0), "pago": Decimal(0), "infraestructura": Decimal(0)}
        detalle = {k: Decimal(0) for k in LECTURAS}
        for f in facturas:
            for fuente, v in self.costos_de(f).items():
                if v is None:
                    continue
                g[GRUPO[fuente]] += v
                if fuente in detalle:
                    detalle[fuente] += v
            parte, _ = self.parte_infra(f)
            g["infraestructura"] += parte or Decimal(0)
        self._detalle_lectura = detalle
        return g

    def costo_por_factura_resuelta(self) -> dict[str, Any]:
        fin = self.finales()
        grupos = self.por_grupo(fin)
        numerador = sum(grupos.values(), Decimal(0))
        abiertas = [f for f in self.facturas.values() if f.estado not in ESTADOS_FINALES]
        en_curso = sum((self.total_de(f, con_infra=False) for f in abiertas), Decimal(0))
        return {"valor_usd": (numerador / len(fin)) if fin else None, "numerador_usd": numerador,
                "denominador": len(fin), "fuentes_usd": grupos, "lectura_usd": dict(self._detalle_lectura),
                "en_curso_usd": en_curso, "abiertas": len(abiertas)}

    def costo_de_pagar(self) -> dict[str, Any]:
        pagadas = [f for f in self.facturas.values() if f.estado == "pagada"]
        num = Decimal(0)
        for f in pagadas:
            c = self.costos_de(f)
            num += (c.get("pago_comision") or Decimal(0)) + (c.get("pago_cambio") or Decimal(0))
        return {"valor_usd": (num / len(pagadas)) if pagadas else None, "numerador_usd": num, "denominador": len(pagadas)}

    def leido_sin_ia(self) -> dict[str, Any]:
        leidas = [fid for fid, evs in self.por_factura.items() if any(e.fuente in LECTURAS for e in evs)]
        sin_ia = [fid for fid in leidas if not any(e.fuente == "lectura_ia" for e in self.por_factura[fid])]
        con_ia = len(leidas) - len(sin_ia)
        return {"pct": round(100 * len(sin_ia) / len(leidas), 1) if leidas else None, "sin_ia": len(sin_ia),
                "con_ia": con_ia, "leidas": len(leidas)}

    def cobertura(self) -> dict[str, Any]:
        """Casillas esperadas: lectura por factura, comisión (y cambio) por orden, revisión por acción, infra por mes."""
        esperadas = conocidas = 0
        indice = {(e.fuente, e.origen_id): e for e in self.eventos}
        for f in self.facturas.values():
            esperadas += 1
            lect = [e for e in self.por_factura.get(f.id, []) if e.fuente in LECTURAS]
            if lect and all(e.importe_nano_usd is not None for e in lect):
                conocidas += 1
        for p in self.pagos:
            casillas = ["pago_comision"] + (["pago_cambio"] if p.moneda_destino != "USD" else [])
            for fuente in casillas:
                esperadas += 1
                e = indice.get((fuente, f"pago:{p.clave_idempotencia}"))
                conocidas += int(e is not None and e.importe_nano_usd is not None)
        for a in self.aprobaciones:
            esperadas += 1
            e = indice.get(("revision_humana", f"aprobacion:{a.id}"))
            conocidas += int(e is not None and e.importe_nano_usd is not None)
        for per in {f.periodo for f in self.facturas.values()}:
            esperadas += 1
            e = self.infra.get(per)
            conocidas += int(e is not None and e.importe_nano_usd is not None)
        return {"pct": round(min(100.0, 100 * conocidas / esperadas), 1) if esperadas else None,
                "conocidas": conocidas, "esperadas": esperadas}

    # -------- recibo
    def recibo(self, f: Factura) -> dict[str, Any]:
        lineas = []
        c = self.costos_de(f)
        lect = [e for e in self.por_factura.get(f.id, []) if e.fuente in LECTURAS]
        if lect:
            caminos = " → ".join({"lectura_xml": "XML", "lectura_texto": "texto", "lectura_ocr": "OCR", "lectura_ia": "IA"}[e.fuente]
                                 for e in lect)
            v = None if any(e.importe_nano_usd is None for e in lect) else sum((a_usd(e.importe_nano_usd) for e in lect), Decimal(0))
            lineas.append({"fuente": "lectura", "titulo": f"Lectura · {caminos}", "importe_usd": v,
                           "detalle": "; ".join(e.detalle for e in lect)})
        revs = [e for e in self.por_factura.get(f.id, []) if e.fuente == "revision_humana"]
        if revs:
            mins = sum((Decimal(str(e.minutos or 0)) for e in revs), Decimal(0))
            lineas.append({"fuente": "revision", "titulo": f"Revisión humana · {mins.normalize()} min", "importe_usd": c.get("revision_humana"),
                           "detalle": "; ".join(e.detalle for e in revs)})
        for fuente, titulo in (("pago_comision", "Comisión del riel"), ("pago_cambio", "Cambio de moneda")):
            if fuente in c:
                evs = [e for e in self.por_factura[f.id] if e.fuente == fuente]
                lineas.append({"fuente": "pago", "titulo": titulo, "importe_usd": c[fuente], "detalle": "; ".join(e.detalle for e in evs)})
        parte, nota = self.parte_infra(f)
        lineas.append({"fuente": "infraestructura", "titulo": "Infraestructura (parte del mes)", "importe_usd": parte, "detalle": nota})
        protegido = None
        if f.estado in ("frenada", "rechazada"):
            protegido = {"usd": f.monto_usd, "texto": f"Kauta evitó pagar {f.monto_usd} USD: {f.motivo[:140]}"}
        elif f.estado == "pagada" and any("R07" in (a.reglas_revisadas or []) for a in self.aprobaciones if a.factura_id == f.id):
            cuenta = f.extraccion.get("cuenta_destino") if f.extraccion else None
            protegido = {"usd": f.monto_usd, "texto": f"Se pagó a la cuenta registrada, no a ···{(cuenta or '')[-4:]} como pedía el documento."}
        desconocido = any(l["importe_usd"] is None for l in lineas)
        return {"factura": f.id, "estado": f.estado, "lineas": lineas, "total_usd": self.total_de(f),
                "total_completo": not desconocido, "protegido": protegido, "simulado": True,
                "calculado_en": self.ahora.isoformat(timespec="seconds") + "Z"}


def _num(v: Decimal | None, nd: int = 2) -> float | None:
    return None if v is None else float(v.quantize(Decimal(10) ** -nd))


def rendimiento(bd: Session, periodo: str | None = None) -> dict[str, Any]:
    lib = Libro(bd, periodo)
    cpr, pagar, sin_ia, cob = lib.costo_por_factura_resuelta(), lib.costo_de_pagar(), lib.leido_sin_ia(), lib.cobertura()
    # «Dónde se va el costo»: todo lo gastado en el mes, también en facturas aún abiertas (la tarjeta usa solo las resueltas)
    fuentes = {k: _num(v, 4) for k, v in lib.por_grupo(list(lib.facturas.values())).items()}
    lectura = {k.replace("lectura_", ""): _num(v, 4) for k, v in lib._detalle_lectura.items()}
    return {
        "periodo": periodo, "calculado_en": lib.ahora.isoformat(timespec="seconds") + "Z", "simulado": True,
        "tarjetas": [
            {"id": "costo_por_factura_resuelta", "titulo": "Costo por factura resuelta", "valor_usd": _num(cpr["valor_usd"]),
             "detalle": f"{cpr['numerador_usd'].quantize(CENT)} USD / {cpr['denominador']} resueltas"},
            {"id": "costo_de_pagar", "titulo": "Costo de pagar una factura", "valor_usd": _num(pagar["valor_usd"]),
             "detalle": f"comisión + cambio / {pagar['denominador']} pagadas"},
            {"id": "leido_sin_ia", "titulo": "Leído sin IA", "valor_pct": sin_ia["pct"],
             "detalle": f"{sin_ia['sin_ia']} de {sin_ia['leidas']} facturas; {sin_ia['con_ia']} con IA"},
            {"id": "cobertura", "titulo": "Cobertura de costos", "valor_pct": cob["pct"],
             "detalle": f"{cob['conocidas']} de {cob['esperadas']} casillas con importe conocido"},
        ],
        "fuentes_usd": fuentes, "lectura_usd": lectura,
        "en_curso_usd": _num(cpr["en_curso_usd"]), "abiertas": cpr["abiertas"],
        "numerador_usd": _num(cpr["numerador_usd"]), "denominador": cpr["denominador"],
    }


def recibo(bd: Session, factura_id: str) -> dict[str, Any] | None:
    f = bd.get(Factura, factura_id)
    if not f:
        return None
    r = Libro(bd, f.periodo).recibo(f)
    r["lineas"] = [{**l, "importe_usd": _num(l["importe_usd"], 4)} for l in r["lineas"]]
    r["total_usd"] = _num(r["total_usd"], 4)
    if r["protegido"]:
        r["protegido"]["usd"] = float(r["protegido"]["usd"] or 0)
    return r


def esperando_firma(bd: Session, correo: str, usuario_id: int) -> list[Factura]:
    fs = bd.execute(select(Factura).where(Factura.estado == "pendiente")).scalars().all()
    return [f for f in fs if f.cargada_por != correo
            and not any(a.usuario_id == usuario_id and a.accion == "aprobar" for a in f.aprobaciones)]


def lente(bd: Session, rol: str, correo: str, usuario_id: int, periodo: str) -> dict[str, Any]:
    """Las tarjetas del Resumen según quién mira. Misma fuente que Rendimiento; máximo 4 tarjetas."""
    m = base(bd)
    lib = Libro(bd, periodo)
    cpr = lib.costo_por_factura_resuelta()
    costo = {"id": "costo_por_factura_resuelta", "titulo": "Costo por factura resuelta", "valor_usd": _num(cpr["valor_usd"]),
             "detalle": f"{cpr['denominador']} resueltas · simulado"}
    protegido = {"id": "dinero_protegido", "titulo": "Dinero protegido", "valor_usd": m["dinero_protegido_usd"],
                 "detalle": f"{m['trampas_detenidas']} de {m['trampas_total']} trampas detenidas"}
    if rol == "cfo":
        pagadas = [f for f in lib.facturas.values() if f.estado == "pagada"]
        pagado = sum((Decimal(f.monto_usd or 0) for f in pagadas), Decimal(0))
        firma = esperando_firma(bd, correo, usuario_id)
        retenido = sum((Decimal(f.monto_usd or 0) for f in firma), Decimal(0))
        return {"pregunta": "¿Cómo va el dinero este mes?", "tarjetas": [
            {"id": "pagado", "titulo": "Pagado", "valor_usd": _num(pagado), "detalle": f"{len(pagadas)} facturas pagadas"},
            {"id": "esperando_firma", "titulo": "Esperando tu firma", "valor": len(firma), "detalle": f"{retenido.quantize(CENT)} USD retenidos"},
            costo, protegido]}
    if rol == "ceo":
        frase = (f"Kauta resolvió sola el {m['autonomia_set_pct']:.0f} % del set, con {m['pagos_fuera_de_reglas']} pagos "
                 f"fuera de reglas y {m['trampas_detenidas']} de {m['trampas_total']} trampas detenidas.")
        return {"pregunta": "¿Kauta está haciendo su trabajo?", "frase": frase, "tarjetas": [
            {"id": "autonomia", "titulo": "Autonomía", "valor_pct": m["autonomia_set_pct"],
             "detalle": f"primera decisión sin persona · {m['set_aciertos']} de {m['set_total']} correctas"},
            {"id": "pagos_indebidos", "titulo": "Pagos indebidos", "valor": m["pagos_fuera_de_reglas"], "detalle": "pagos fuera de las reglas"},
            protegido]}
    sin_ia, cob = lib.leido_sin_ia(), lib.cobertura()
    return {"pregunta": "¿El agente es eficiente?", "tarjetas": [
        costo,
        {"id": "leido_sin_ia", "titulo": "Leído sin IA", "valor_pct": sin_ia["pct"], "detalle": f"{sin_ia['con_ia']} con IA de {sin_ia['leidas']}"},
        {"id": "cobertura", "titulo": "Cobertura de costos", "valor_pct": cob["pct"], "detalle": f"{cob['conocidas']} de {cob['esperadas']} casillas"}]}
