"""Pantalla inicial: elegir una de las tres personas de la demo (CFO/CEO/CTO), un clic
como el jurado — igual que /api/auth/demo ofrece al frontend."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static
from textual.widgets.option_list import Option

from ..client import ErrorKauta
from ..widgets.modales import PedirTexto

LOGO = r"""
 _               _
| | ____ _ _   _| |_ __ _
| |/ / _` | | | | __/ _` |
|   < (_| | |_| | || (_| |
|_|\_\__,_|\__,_|\__\__,_|
"""


class Persona(Option):
    def __init__(self, correo: str, nombre: str, cargo: str, rol_nombre: str):
        super().__init__(f"{nombre}  [dim]({cargo} · {rol_nombre})[/dim]")
        self.correo = correo


class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        from textual.widgets import OptionList
        with Middle():
            with Center():
                yield Static(LOGO, classes="titulo")
            with Center():
                yield Static("Libro de costos FinOps · elige con quién entras", classes="tenue")
            with Center():
                yield OptionList(id="personas")
            with Center():
                yield Static("", id="error", classes="mal")

    def on_mount(self) -> None:
        self._cargar()

    @work
    async def _cargar(self) -> None:
        lista = self.query_one("#personas")
        app = self.app
        try:
            datos = await app.cliente.personas_demo()
        except ErrorKauta:
            # No estamos en modo demo: solo queda el login con correo y contraseña.
            await self._pedir_credenciales()
            return
        for u in datos["usuarios"]:
            lista.add_option(Persona(u["correo"], u["nombre"], u["cargo"], u["rol_nombre"]))

    async def on_option_list_option_selected(self, evento) -> None:
        correo = evento.option.correo
        app = self.app
        try:
            usuario = await app.cliente.entrar_como(correo)
        except ErrorKauta as e:
            self.query_one("#error", Static).update(f"No se pudo entrar: {e.detail}")
            return
        app.entrar(usuario)

    async def _pedir_credenciales(self) -> None:
        app = self.app
        correo = await app.push_screen_wait(PedirTexto("Correo", placeholder="nombre@empresa.example"))
        if not correo:
            return
        contrasena = await app.push_screen_wait(PedirTexto("Contraseña", placeholder="••••••••"))
        if not contrasena:
            return
        try:
            usuario = await app.cliente.iniciar_sesion(correo, contrasena)
        except ErrorKauta as e:
            self.query_one("#error", Static).update(f"No se pudo entrar: {e.detail}")
            return
        if usuario.get("mfa_requerido"):
            codigo = await app.push_screen_wait(PedirTexto("Código TOTP"))
            if not codigo:
                return
            usuario = await app.cliente.iniciar_sesion(correo, contrasena, codigo)
        await app.entrar(usuario)
