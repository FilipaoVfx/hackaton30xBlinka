"""Modales livianos reutilizados por las pantallas: pedir un texto o confirmar una acción."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static


class PedirTexto(ModalScreen[str | None]):
    """Pide una línea de texto (comentario, monto...) y devuelve el valor o None si se cancela."""

    def __init__(self, titulo: str, placeholder: str = "", valor_inicial: str = ""):
        super().__init__(id="modal-dialogo")
        self._titulo = titulo
        self._placeholder = placeholder
        self._valor_inicial = valor_inicial

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._titulo, classes="titulo")
            yield Input(value=self._valor_inicial, placeholder=self._placeholder, id="campo")
            yield Static("[dim]enter = confirmar · esc = cancelar[/dim]")

    def on_mount(self) -> None:
        self.query_one("#campo", Input).focus()

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        self.dismiss(evento.value.strip() or None)

    def on_key(self, evento) -> None:
        if evento.key == "escape":
            self.dismiss(None)


class Confirmar(ModalScreen[bool]):
    """Sí/no simple con dos botones, para acciones destructivas (rechazar, etc.)."""

    def __init__(self, pregunta: str):
        super().__init__(id="modal-dialogo")
        self._pregunta = pregunta

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._pregunta, classes="titulo")
            yield Button("Confirmar", variant="error", id="si")
            yield Button("Cancelar", id="no")

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        self.dismiss(evento.button.id == "si")

    def on_key(self, evento) -> None:
        if evento.key == "escape":
            self.dismiss(False)
