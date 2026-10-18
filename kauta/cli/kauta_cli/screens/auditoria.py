"""Auditoría en vivo, tipo 'tail -f' de k9s: solo se agregan los eventos nuevos
(por id), nunca se reconstruye el log entero — así el refresco a 1s no cuesta nada."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.widgets import RichLog, Static

from .base import PantallaBase

INTERVALO_S = 1.0
COLOR_TIPO = {"seguridad": "#FFB547", "factura": "#3B5BFD", "pago": "#16C79A", "wallet": "#16C79A",
              "reglas": "#9DADFF", "cuenta": "#FF5C5C", "auditoria": "#5B6782"}


def _color(tipo: str) -> str:
    return COLOR_TIPO.get(tipo.split(".")[0], "#F5F7FB")


class AuditoriaScreen(PantallaBase):
    NOMBRE = "Auditoría"
    _ultimo_id = 0

    def compose(self) -> ComposeResult:
        yield from self.compose_cabecera()
        yield Static("", id="cadena")
        yield RichLog(id="log", markup=True, wrap=True, max_lines=500)

    def on_mount(self) -> None:
        super().on_mount()
        self._ultimo_id = 0
        self._refrescar()
        self.set_interval(INTERVALO_S, self._refrescar)

    def action_refrescar(self) -> None:
        self._ultimo_id = 0
        self.query_one("#log", RichLog).clear()
        self._refrescar()

    @work(exclusive=True)
    async def _refrescar(self) -> None:
        datos = await self.intentar(self.app.cliente.auditoria(limite=300), "en vivo")
        if datos is None:
            return
        verificacion = datos.get("verificacion", {})
        color = "#16C79A" if verificacion.get("ok") else "#FF5C5C"
        self.query_one("#cadena", Static).update(f"Cadena HMAC: [{color}]{verificacion.get('mensaje', '?')}[/]")
        nuevos = [e for e in datos["eventos"] if e["id"] > self._ultimo_id]
        if not nuevos:
            return
        log = self.query_one("#log", RichLog)
        for e in sorted(nuevos, key=lambda x: x["id"]):
            log.write(f"[dim]{e['ts'][11:19]}[/dim] [{_color(e['tipo'])}]{e['tipo']:<28}[/] {e['actor']:<22} {e['resumen']}")
            self._ultimo_id = max(self._ultimo_id, e["id"])
