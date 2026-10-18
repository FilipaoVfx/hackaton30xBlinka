"""Barra de navegación tipo k9s: números para saltar de pantalla, siempre visible."""
from __future__ import annotations

from textual.widgets import Static

OPCIONES = [
    ("1", "Resumen"), ("2", "Facturas"), ("3", "Wallet"), ("4", "Pagos"),
    ("5", "Auditoría"), ("6", "Simulador"), ("p", "Persona"), ("q", "Salir"),
]


class Menu(Static):
    def __init__(self, activa: str = ""):
        super().__init__(id="menu")
        self._activa = activa

    def on_mount(self) -> None:
        partes = []
        for tecla, nombre in OPCIONES:
            if nombre == self._activa:
                partes.append(f"[reverse b] {tecla} {nombre} [/]")
            else:
                partes.append(f"[dim]{tecla}[/dim] {nombre}")
        self.update("  ·  ".join(partes))
