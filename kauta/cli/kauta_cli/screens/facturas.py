"""Bandeja de facturas: listar, ver detalle, aprobar/rechazar — on-demand (sin
polling constante, solo al entrar o al pedir refresco con 'r')."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Static

from ..widgets.modales import Confirmar, PedirTexto
from .base import PantallaBase


class FacturasScreen(PantallaBase):
    NOMBRE = "Facturas"
    BINDINGS = [
        ("a", "aprobar", "Aprobar"),
        ("x", "rechazar", "Rechazar"),
        ("r", "refrescar", "Refrescar"),
    ]

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        with Horizontal():
            yield DataTable(id="facturas", cursor_type="row")
            with VerticalScroll(classes="panel", id="detalle-col"):
                yield Static("Selecciona una factura (↑↓, enter)", classes="panel-titulo")
                yield Static("", id="detalle")

    _fid_actual: str | None = None

    def on_mount(self) -> None:
        super().on_mount()
        tabla = self.query_one("#facturas", DataTable)
        tabla.add_columns("ID", "Beneficiario", "Monto USD", "Decisión", "Estado", "Motivo")
        self._refrescar()

    def action_refrescar(self) -> None:
        self._refrescar()

    @work(exclusive=True)
    async def _refrescar(self) -> None:
        facturas = await self.intentar(self.app.cliente.facturas(), "actualizado")
        if facturas is None:
            return
        tabla = self.query_one("#facturas", DataTable)
        fila_actual = tabla.cursor_row
        tabla.clear()
        for f in facturas:
            tabla.add_row(
                f["id"], f["beneficiario"][:28], f"{f.get('monto_usd') or 0:,.2f}",
                f["decision"], f["estado"], (f.get("motivo") or "")[:40], key=f["id"],
            )
        if facturas and fila_actual is not None and fila_actual < len(facturas):
            tabla.move_cursor(row=fila_actual)

    def on_data_table_row_highlighted(self, evento: DataTable.RowHighlighted) -> None:
        if evento.row_key.value:
            self._fid_actual = str(evento.row_key.value)
            self._mostrar_detalle(self._fid_actual)

    @work(exclusive=True)
    async def _mostrar_detalle(self, fid: str) -> None:
        # tocar_ok=False: esto se dispara en cada cambio de cursor (incluido el que
        # provoca el propio refresco tras aprobar/rechazar) y no debe tapar el
        # mensaje de resultado de esa acción con un "listo" genérico.
        f = await self.intentar(self.app.cliente.factura(fid), tocar_ok=False)
        if f is None:
            return
        reglas = "\n".join(f"  [{'#16C79A' if r['estado'] == 'cumple' else '#FF5C5C' if r['estado'] == 'falla' else '#5B6782'}]"
                            f"{r['estado']:>8}[/] {r['nombre']}" for r in f.get("reglas", []))
        self.query_one("#detalle", Static).update(
            f"[b]{f['id']}[/b] · {f['beneficiario']}\n"
            f"Monto: {f.get('moneda')} {f.get('monto') or 0:,.2f} (USD {f.get('monto_usd') or 0:,.2f})\n"
            f"Estado: {f['estado']}  ·  Decisión: {f['decision']}\n"
            f"Motivo: {f.get('motivo') or '—'}\n\n"
            f"Reglas:\n{reglas or '  (sin reglas evaluadas)'}"
        )

    def action_aprobar(self) -> None:
        if self._fid_actual:
            self._flujo_aprobar(self._fid_actual)

    def action_rechazar(self) -> None:
        if self._fid_actual:
            self._flujo_rechazar(self._fid_actual)

    @work
    async def _flujo_aprobar(self, fid: str) -> None:
        comentario = await self.app.push_screen_wait(
            PedirTexto(f"Aprobar {fid} · comentario", valor_inicial="Aprobado desde la CLI")
        )
        if comentario is None:
            return
        resultado = await self.intentar(self.app.cliente.aprobar_factura(fid, comentario), f"{fid} aprobada")
        if resultado is not None:
            self._refrescar()

    @work
    async def _flujo_rechazar(self, fid: str) -> None:
        confirmar = await self.app.push_screen_wait(Confirmar(f"¿Rechazar la factura {fid}?"))
        if not confirmar:
            return
        resultado = await self.intentar(self.app.cliente.rechazar_factura(fid, "Rechazada desde la CLI"), f"{fid} rechazada")
        if resultado is not None:
            self._refrescar()
