"""Formas de los datos que llegan de la API (espejo de ``servidor/esquemas.py`` /
``web/src/api.ts``). Son ``TypedDict`` — sin costo en tiempo de ejecución, solo para
que las pantallas accedan a los campos correctos sin reescribirlos a mano cada vez.
"""
from __future__ import annotations

from typing import TypedDict


class Usuario(TypedDict, total=False):
    id: int
    correo: str
    nombre: str
    cargo: str
    rol: str
    rol_nombre: str
    mfa_activo: bool
    permisos: list[str]
    csrf: str | None


class Regla(TypedDict, total=False):
    id: str
    nombre: str
    efecto: str
    estado: str
    detalle: str


class FacturaResumen(TypedDict, total=False):
    id: str
    archivo: str
    beneficiario: str
    numero: str | None
    monto: float | None
    moneda: str | None
    monto_usd: float | None
    periodo: str
    decision: str
    estado: str
    motivo: str
    regla: str
    recibida_en: str
    reglas: list[Regla]
    pago: dict | None


class Pago(TypedDict, total=False):
    id: str
    factura_id: str
    beneficiario: str
    riel: str
    riel_nombre: str
    estado: str
    monto_usd: float
    comision_usd: float
    costo_fx_usd: float
    moneda_destino: str
    monto_destino: float
    creado_en: str
    liquidado_en: str | None
    motivo_devolucion: str | None


class EventoAuditoria(TypedDict, total=False):
    id: int
    ts: str
    tipo: str
    actor: str
    entidad: str | None
    entidad_id: str | None
    resumen: str
    hash: str
    hash_anterior: str | None
