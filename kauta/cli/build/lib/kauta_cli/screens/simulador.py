"""El momento central de la demo: dispara /api/simulador/anio (un año completo de
facturas evaluado por el motor de reglas, en memoria) y revela el resultado real
con un conteo animado — la animación es solo una presentación de datos reales, el
número final siempre es el que devolvió el servidor, nunca uno inventado."""
from __future__ import annotations

import asyncio
import time

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import LoadingIndicator, Static

from .base import PantallaBase

PASOS_ANIMACION = 18
DURACION_ANIMACION_S = 0.6


class SimuladorScreen(PantallaBase):
    NOMBRE = "Simulador"
    BINDINGS = [("a", "simular", "Simular un año")]
    _ejecutando = False

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        with Vertical(classes="panel"):
            yield Static(
                "[b]a[/b] · simula un año completo de facturas contra el motor de 13 reglas.\n"
                "Todo ocurre en memoria en el servidor — el número de abajo es el tiempo real.",
                id="instrucciones",
            )
            with Horizontal(id="fila-carga"):
                yield LoadingIndicator(id="carga")
            with Horizontal():
                yield Static("", id="resultado-numeros")
            yield Static("", id="resultado-detalle")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#fila-carga").display = False

    def action_simular(self) -> None:
        if not self._ejecutando:
            self._simular()

    @work(exclusive=True)
    async def _simular(self) -> None:
        self._ejecutando = True
        carga = self.query_one("#fila-carga")
        carga.display = True
        self.query_one("#resultado-numeros", Static).update("")
        self.query_one("#resultado-detalle", Static).update("")
        t0 = time.perf_counter()
        resultado = await self.intentar(self.app.cliente.simular_anio(), "simulación lista")
        transcurrido_cliente = time.perf_counter() - t0
        carga.display = False
        self._ejecutando = False
        if resultado is None:
            return
        await self._revelar(resultado, transcurrido_cliente)

    async def _revelar(self, r: dict, transcurrido_cliente: float) -> None:
        objetivo = {
            "total": r["total"], "pagado_usd": r["pagado_usd"], "protegido_usd": r["protegido_usd"],
            "autonomia_pct": r["autonomia_pct"],
        }
        numeros = self.query_one("#resultado-numeros", Static)
        for paso in range(1, PASOS_ANIMACION + 1):
            avance = paso / PASOS_ANIMACION
            numeros.update(
                f"[b]{int(objetivo['total'] * avance):>4}[/] facturas   "
                f"USD [b #16C79A]{objetivo['pagado_usd'] * avance:>12,.0f}[/] pagadas   "
                f"USD [b #FFB547]{objetivo['protegido_usd'] * avance:>10,.0f}[/] protegidas   "
                f"[b]{objetivo['autonomia_pct'] * avance:>5.1f}%[/] autónomo"
            )
            await asyncio.sleep(DURACION_ANIMACION_S / PASOS_ANIMACION)
        por_tipo = "  ·  ".join(f"{t}: {sum(c.values())}" for t, c in r.get("por_tipo", {}).items())
        self.query_one("#resultado-detalle", Static).update(
            f"{r['meses']} meses · {r['total']} facturas evaluadas en {r['segundos']:.3f}s en el servidor "
            f"({r['ms_por_factura']:.2f} ms/factura) · ida y vuelta por la red: {transcurrido_cliente:.3f}s\n"
            f"Pagos indebidos: {r['pagos_indebidos']}  ·  Trampas detenidas: "
            f"{r['trampas'] - r['trampas_pagadas']}/{r['trampas']}\n"
            f"Por tipo de caso: {por_tipo}"
        )
