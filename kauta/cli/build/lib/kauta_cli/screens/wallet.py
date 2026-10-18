"""Wallet de doble partida: saldos por cuenta y últimos asientos. On-demand."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Static

from ..widgets.barra_estado import BarraEstado
from ..widgets.modales import PedirTexto
from .base import PantallaBase


class WalletScreen(PantallaBase):
    NOMBRE = "Wallet"
    BINDINGS = [("f", "fondear", "Fondear"), ("r", "refrescar", "Refrescar")]

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        with Horizontal():
            with Vertical(classes="panel", id="col-cuentas"):
                yield Static("Cuentas", classes="panel-titulo")
                yield DataTable(id="cuentas", cursor_type="none")
            with VerticalScroll(classes="panel", id="col-libro"):
                yield Static("Libro · últimos asientos", classes="panel-titulo")
                yield Static("", id="libro")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#cuentas", DataTable).add_columns("Cuenta", "Tipo", "Saldo USD")
        self._refrescar()

    def action_refrescar(self) -> None:
        self._refrescar()

    @work(exclusive=True)
    async def _refrescar(self) -> None:
        w = await self.intentar(self.app.cliente.wallet(), "actualizado")
        if w is None:
            return
        tabla = self.query_one("#cuentas", DataTable)
        tabla.clear()
        for c in w.get("cuentas", []):
            tabla.add_row(c["nombre"], c["tipo"], f"{c['saldo']:,.2f}")
        verificacion = w.get("libro", {})
        asientos = "\n".join(
            f"[dim]{a['fecha'][:19]}[/dim]  {a['tipo']:<10} {a['descripcion'][:60]}"
            for a in w.get("asientos", [])[:25]
        )
        estado_libro = "[#16C79A]cuadrado[/]" if verificacion.get("ok") else "[#FF5C5C]desbalanceado[/]"
        self.query_one("#libro", Static).update(f"Libro mayor: {estado_libro}\n\n{asientos or '(sin asientos)'}")

    def action_fondear(self) -> None:
        self._flujo_fondear()

    @work
    async def _flujo_fondear(self) -> None:
        texto = await self.app.push_screen_wait(
            PedirTexto("Fondear operativa · monto USD", valor_inicial="1000")
        )
        if not texto:
            return
        try:
            monto = float(texto.replace(",", ""))
        except ValueError:
            self.query_one("#barra", BarraEstado).error("Monto inválido")
            return
        resultado = await self.intentar(self.app.cliente.fondear_wallet(monto), f"fondeado USD {monto:,.2f}")
        if resultado is not None:
            self._refrescar()
