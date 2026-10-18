"""Dashboard: lo primero que ve el jurado tras entrar. Métricas + wallet + sparkline
con refresco cada 2.5s — volátil pero barato (una sola llamada a /api/resumen)."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Sparkline, Static

from .base import PantallaBase

INTERVALO_S = 2.5


class ResumenScreen(PantallaBase):
    NOMBRE = "Resumen"

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        with Horizontal():
            with Vertical(classes="panel", id="col-metricas"):
                yield Static("Métricas", classes="panel-titulo")
                yield Static("", id="metricas")
            with Vertical(classes="panel", id="col-wallet"):
                yield Static("Wallet", classes="panel-titulo")
                yield Static("", id="wallet")
                yield Sparkline([], id="sparkline")
        with VerticalScroll(classes="panel"):
            yield Static("Últimas facturas", classes="panel-titulo")
            yield DataTable(id="ultimas", cursor_type="row")

    def on_mount(self) -> None:
        super().on_mount()
        tabla = self.query_one("#ultimas", DataTable)
        tabla.add_columns("ID", "Beneficiario", "Monto USD", "Decisión", "Estado")
        self._refrescar()
        self.set_interval(INTERVALO_S, self._refrescar)

    def action_refrescar(self) -> None:
        self._refrescar()

    @work(exclusive=True)
    async def _refrescar(self) -> None:
        datos = await self.intentar(self.app.cliente.resumen(), "actualizado")
        if datos is None or not self.is_attached:
            return
        m = datos["metricas"]
        self.query_one("#metricas", Static).update(
            f"Autonomía:  [b #16C79A]{m['autonomia_pct']:.0f}%[/]\n"
            f"Explicabilidad:  [b]{m['explicadas_pct']:.0f}%[/]\n"
            f"Pagos indebidos:  [b {'#16C79A' if m['pagos_fuera_de_reglas'] == 0 else '#FF5C5C'}]"
            f"{m['pagos_fuera_de_reglas']}[/]\n"
            f"Periodo: {datos['periodo']} · reglas v{datos['version_reglas']}"
        )
        w = datos["wallet"]
        self.query_one("#wallet", Static).update(
            f"Presupuesto: USD {datos['presupuesto']:,.2f}\n"
            f"Operativa: USD {w.get('operativa', 0):,.2f}\n"
            f"Disponible CxP: USD {w.get('disponible_cxp', 0):,.2f}\n"
            f"Costos (comisión+FX): USD {w.get('costos', 0):,.2f}"
        )
        serie = [p["acumulado"] for p in datos["serie"][-60:]] or [0]
        self.query_one("#sparkline", Sparkline).data = serie
        tabla = self.query_one("#ultimas", DataTable)
        tabla.clear()
        for f in datos["ultimas"]:
            tabla.add_row(f["id"], f["beneficiario"][:28], f"{f.get('monto_usd') or 0:,.2f}", f["decision"], f["estado"])
