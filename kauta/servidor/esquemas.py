"""
Esquemas de entrada de la API (Pydantic v2): todo dato que llega de afuera se valida con tipos,
rangos y largos máximos antes de tocar la lógica. Los campos desconocidos se rechazan.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Correo con el mismo formato en todas las entradas (sin depender de una librería externa)
Correo = Annotated[str, Field(min_length=3, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]

Texto = Annotated[str, Field(max_length=1000)]


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonaIn(Estricto):
    correo: Correo


class LoginIn(Estricto):
    correo: Correo
    contrasena: Annotated[str, Field(min_length=1, max_length=200)]
    codigo: Annotated[str | None, Field(max_length=10)] = None


class CodigoIn(Estricto):
    codigo: Annotated[str, Field(min_length=6, max_length=10)]


class Correcciones(Estricto):
    monto: Annotated[float | None, Field(gt=0, lt=10_000_000)] = None
    moneda: Annotated[str | None, Field(pattern=r"^[A-Z]{3}$")] = None
    numero_factura: Annotated[str | None, Field(max_length=60)] = None
    horas: Annotated[float | None, Field(gt=0, lt=1000)] = None


class AprobarIn(Estricto):
    comentario: Annotated[str, Field(min_length=1, max_length=1000)]
    correcciones: Correcciones | None = None
    codigo_totp: Annotated[str | None, Field(max_length=10)] = None


class RechazarIn(Estricto):
    comentario: Annotated[str, Field(min_length=1, max_length=1000)]


class ReglasIn(Estricto):
    presupuesto_periodo_usd: Annotated[float, Field(ge=0, le=10_000_000)]
    umbral_aprobacion_usd: Annotated[float, Field(ge=0, le=10_000_000)]
    limite_maximo_pago_usd: Annotated[float, Field(ge=0, le=10_000_000)]
    limite_beneficiario_periodo_usd: Annotated[float, Field(ge=0, le=10_000_000)]
    tolerancia_contrato_pct: Annotated[float, Field(ge=0, le=100)]
    confianza_minima: Annotated[float, Field(ge=0.5, le=1)]
    monedas_permitidas: Annotated[list[Annotated[str, Field(pattern=r"^[A-Z]{3}$")]], Field(min_length=1, max_length=10)]
    motivo: Annotated[str, Field(min_length=3, max_length=500)]

    @model_validator(mode="after")
    def _coherencia(self) -> "ReglasIn":
        if self.umbral_aprobacion_usd > self.limite_maximo_pago_usd:
            raise ValueError("El umbral de aprobación no puede ser mayor que el máximo por pago.")
        return self


class SimFacturaIn(Estricto):
    escenario: Annotated[str | None, Field(max_length=30)] = None
    beneficiario_id: Annotated[str | None, Field(max_length=12)] = None
    nombre: Annotated[str, Field(min_length=2, max_length=160)]
    id_fiscal: Annotated[str | None, Field(max_length=40)] = None
    pais: Annotated[str | None, Field(pattern=r"^[A-Z]{2}$")] = None
    numero: Annotated[str, Field(min_length=1, max_length=60)]
    fecha_emision: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    fecha_vencimiento: Annotated[str | None, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None
    moneda: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    monto: Annotated[float, Field(gt=0, lt=10_000_000)]
    horas: Annotated[float | None, Field(gt=0, lt=1000)] = None
    concepto: Annotated[str | None, Field(max_length=300)] = None
    cuenta: Annotated[str | None, Field(pattern=r"^\d{4}$")] = None
    nota_documento: Annotated[str, Field(max_length=2000)] = ""
    confianza_monto: Annotated[float, Field(ge=0, le=1)] = 0.99
    forzar_devolucion: bool = False
    riel: Annotated[str | None, Field(max_length=12)] = None


class SimAnioIn(Estricto):
    meses: Annotated[int, Field(ge=1, le=36)] = 12
    trampas_pct: Annotated[int, Field(ge=0, le=90)] = 30
    semilla: Annotated[int, Field(ge=0, le=1_000_000)] = 7


class VerificarCambioIn(Estricto):
    aprobar: bool
    metodo: Annotated[str, Field(min_length=3, max_length=200)]
    comentario: Annotated[str, Field(max_length=500)] = ""


class FondearIn(Estricto):
    monto: Annotated[float, Field(gt=0, le=1_000_000)]


class InvitarIn(Estricto):
    correo: Correo
    nombre: str = Field(min_length=2, max_length=120)
    cargo: str = Field(default="", max_length=120)
    rol: Literal["ceo", "cfo", "cto"]


class RegistroIn(Estricto):
    correo: Correo
    codigo: str = Field(min_length=6, max_length=40)
    contrasena: str = Field(min_length=15, max_length=200)


class RolIn(Estricto):
    rol: Literal["ceo", "cfo", "cto"]


class ActivoIn(Estricto):
    activo: bool


class CambioContrasenaIn(Estricto):
    actual: str = Field(min_length=1, max_length=200)
    nueva: str = Field(min_length=15, max_length=200)


class RestablecerIn(Estricto):
    con_set: bool = True


class ReintentarIn(Estricto):
    riel: Annotated[str | None, Field(max_length=12)] = None


Rol = Literal["ceo", "cfo", "cto"]
