"""Barra superior: quién soy, qué rol, y si la última llamada a la API falló."""
from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static


class BarraEstado(Static):
    usuario_texto: reactive[str] = reactive("")
    estado_texto: reactive[str] = reactive("conectando…")
    es_error: reactive[bool] = reactive(False)

    def fijar_usuario(self, usuario: dict) -> None:
        self.usuario_texto = f"[b]{usuario.get('nombre', '?')}[/b] · {usuario.get('rol_nombre', usuario.get('rol', '?'))}"
        self._refrescar()

    def ok(self, mensaje: str) -> None:
        self.estado_texto, self.es_error = mensaje, False
        self._refrescar()

    def error(self, mensaje: str) -> None:
        self.estado_texto, self.es_error = mensaje, True
        self._refrescar()

    def _refrescar(self) -> None:
        clase = "#FF5C5C" if self.es_error else "#16C79A"
        self.update(f"{self.usuario_texto}   [{clase}]{self.estado_texto}[/]")
