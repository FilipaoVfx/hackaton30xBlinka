"""Pagos ejecutados por el simulador de rieles: lista + reintentar los devueltos."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.widgets import DataTable

from .base import PantallaBase

COLOR_ESTADO = {"liquidado": "#16C79A", "reservado": "#FFB547", "enviado": "#3B5BFD", "devuelto": "#FF5C5C"}


class PagosScreen(PantallaBase):
    NOMBRE = "Pagos"
    BINDINGS = [("t", "reintentar", "Reintentar"), ("r", "refrescar", "Refrescar")]
    _pid_actual: str | None = None

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        yield DataTable(id="pagos", cursor_type="row")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#pagos", DataTable).add_columns(
            "ID", "Factura", "Beneficiario", "Riel", "Costo total USD", "Estado"
        )
        self._refrescar()

    def action_refrescar(self) -> None:
        self._refrescar()

    @work(exclusive=True)
    async def _refrescar(self) -> None:
        pagos = await self.intentar(self.app.cliente.pagos(), "actualizado")
        if pagos is None:
            return
        tabla = self.query_one("#pagos", DataTable)
        fila = tabla.cursor_row
        tabla.clear()
        for p in pagos:
            costo = (p.get("monto_usd") or 0) + (p.get("comision_usd") or 0) + (p.get("costo_fx_usd") or 0)
            color = COLOR_ESTADO.get(p["estado"], "#B5BFD3")
            tabla.add_row(
                p["id"], p["factura_id"], p["beneficiario"][:24], p["riel_nombre"],
                f"{costo:,.2f}", f"[{color}]{p['estado']}[/]", key=p["id"],
            )
        if pagos and fila is not None and fila < len(pagos):
            tabla.move_cursor(row=fila)

    def on_data_table_row_highlighted(self, evento: DataTable.RowHighlighted) -> None:
        if evento.row_key.value:
            self._pid_actual = str(evento.row_key.value)

    def action_reintentar(self) -> None:
        if self._pid_actual:
            self._flujo_reintentar(self._pid_actual)

    @work
    async def _flujo_reintentar(self, pid: str) -> None:
        resultado = await self.intentar(self.app.cliente.reintentar_pago(pid), f"{pid} reintentado")
        if resultado is not None:
            self._refrescar()
