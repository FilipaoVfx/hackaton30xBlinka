"""TUI de Kauta: otra forma de consumir la misma API que ya usa el frontend React,
pensada para una demo de terminal rápida (paneles vivos, navegación por teclado)
sin sacrificar performance por efectos cosméticos."""
from __future__ import annotations

import argparse
import os

from textual.app import App
from textual.binding import Binding

from .client import KautaClient
from .screens.auditoria import AuditoriaScreen
from .screens.facturas import FacturasScreen
from .screens.login import LoginScreen
from .screens.pagos import PagosScreen
from .screens.resumen import ResumenScreen
from .screens.simulador import SimuladorScreen
from .screens.wallet import WalletScreen

PANTALLAS = {
    "1": ResumenScreen, "2": FacturasScreen, "3": WalletScreen,
    "4": PagosScreen, "5": AuditoriaScreen, "6": SimuladorScreen,
}


class KautaApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "Kauta"

    BINDINGS = [
        Binding("1", "ir('1')", "Resumen", show=False),
        Binding("2", "ir('2')", "Facturas", show=False),
        Binding("3", "ir('3')", "Wallet", show=False),
        Binding("4", "ir('4')", "Pagos", show=False),
        Binding("5", "ir('5')", "Auditoría", show=False),
        Binding("6", "ir('6')", "Simulador", show=False),
        Binding("p", "cambiar_persona", "Cambiar persona", show=False),
        Binding("q", "quit", "Salir", show=False),
    ]

    def __init__(self, base_url: str):
        super().__init__()
        self.cliente = KautaClient(base_url)
        self.usuario: dict | None = None

    async def on_mount(self) -> None:
        await self.push_screen(LoginScreen())

    async def on_unmount(self) -> None:
        await self.cliente.aclose()

    def entrar(self, usuario: dict) -> None:
        self.usuario = usuario
        self.sub_title = f"{usuario.get('nombre', '?')} · {usuario.get('rol_nombre', '?')}"
        # Sin await: switch_screen agenda su propia continuación en la cola de la app
        # (AwaitComplete.call_next); esperarla aquí, dentro del manejador que la
        # disparó, la dejaría encerrada en una vuelta de bucle de mensajes bloqueada.
        self.switch_screen(ResumenScreen())

    def ir_a_factura(self, fid: str) -> None:
        """Desde el resumen: abrir Facturas ya parado sobre esa factura."""
        if self.usuario is not None:
            self.switch_screen(FacturasScreen(fid))

    def action_ir(self, tecla: str) -> None:
        if self.usuario is None:
            return
        pantalla = PANTALLAS[tecla]
        if isinstance(self.screen, pantalla):
            return
        self.switch_screen(pantalla())

    async def action_cambiar_persona(self) -> None:
        if self.usuario is None:
            return
        await self.cliente.cerrar_sesion()
        self.usuario = None
        self.sub_title = ""
        self.switch_screen(LoginScreen())


# La demo pública: así `kauta` sin argumentos funciona desde cualquier máquina.
# Para un backend local: kauta --url http://127.0.0.1:8000
API_DEMO = "https://kauta.2-25-233-186.sslip.io"


def main() -> None:
    parser = argparse.ArgumentParser(description="Kauta CLI — TUI de terminal para la API de Kauta.")
    parser.add_argument("--url", default=os.environ.get("KAUTA_URL", API_DEMO),
                         help=f"Base de la API de Kauta (por defecto la demo pública: {API_DEMO}).")
    args = parser.parse_args()
    KautaApp(args.url).run()


if __name__ == "__main__":
    main()
