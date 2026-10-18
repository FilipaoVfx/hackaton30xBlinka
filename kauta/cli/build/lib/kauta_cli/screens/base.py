"""Base común a todas las pantallas autenticadas: cabecera (usuario + estado) y menú
de navegación siempre visibles, más un helper para no repetir el manejo de errores
de red en cada pantalla."""
from __future__ import annotations

from typing import Awaitable, TypeVar

from textual.app import ComposeResult
from textual.screen import Screen

from ..client import ErrorKauta
from ..widgets.barra_estado import BarraEstado
from ..widgets.menu import Menu

T = TypeVar("T")


class PantallaBase(Screen):
    NOMBRE = ""
    BINDINGS = [("r", "refrescar", "Refrescar")]

    def compose_cabecera(self) -> ComposeResult:
        yield BarraEstado(id="barra")
        yield Menu(self.NOMBRE)

    def on_mount(self) -> None:
        barra = self.query_one("#barra", BarraEstado)
        if getattr(self.app, "usuario", None):
            barra.fijar_usuario(self.app.usuario)
        barra.ok("listo")

    async def intentar(self, corutina: Awaitable[T], mensaje_ok: str = "listo", *, tocar_ok: bool = True) -> T | None:
        barra = self.query_one("#barra", BarraEstado)
        try:
            resultado = await corutina
        except ErrorKauta as e:
            barra.error(f"{e.status}: {e.detail}")
            return None
        except Exception as e:  # red caída, timeout, etc. — nunca debe tumbar la TUI
            barra.error(str(e))
            return None
        if tocar_ok:
            barra.ok(mensaje_ok)
        return resultado

    def action_refrescar(self) -> None:
        pass  # cada pantalla concreta sobreescribe esto
