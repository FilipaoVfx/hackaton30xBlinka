"""
Modelo de datos de Kauta (SQLAlchemy 2.0, tipado). Un archivo por dominio sería lo habitual en un
equipo grande; aquí se agrupa para que el jurado vea todo el esquema en un solo lugar.

Convenciones:
  * Montos en NUMERIC(18,2): nunca float para dinero.
  * Fechas en UTC.
  * Datos bancarios y secretos MFA cifrados con AES-256-GCM (columna *_cifrada).
  * Las tablas de auditoría y del libro mayor solo reciben INSERT (se verifican con hash/HMAC).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import event
from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

DINERO = Numeric(18, 2)
TASA = Numeric(18, 6)


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Identidad y acceso
# ---------------------------------------------------------------------------
class Organizacion(Base):
    __tablename__ = "organizaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    id_fiscal: Mapped[str] = mapped_column(String(40))
    datos: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    cargo: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    hash_contrasena: Mapped[str] = mapped_column(String(255))
    totp_cifrado: Mapped[str | None] = mapped_column(Text)
    mfa_activo: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_ultimo_paso: Mapped[int | None] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (CheckConstraint("rol IN ('ceo','cfo','cto')", name="ck_rol"),)


class Invitacion(Base):
    """
    Alta de usuarios por invitación: una empresa no deja que cualquiera se registre con su correo.
    Alguien de administración crea la invitación con el rol que tendrá la persona; el código se
    guarda solo como hash (igual que una contraseña) y se entrega una vez.
    """
    __tablename__ = "invitaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(String(160), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    cargo: Mapped[str] = mapped_column(String(120))
    rol: Mapped[str] = mapped_column(String(20))
    hash_codigo: Mapped[str] = mapped_column(String(255))
    prefijo: Mapped[str] = mapped_column(String(8))          # para reconocerla en la lista, sin revelar el código
    creada_por: Mapped[str] = mapped_column(String(160))
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    usada_en: Mapped[datetime | None] = mapped_column(DateTime)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        CheckConstraint("rol IN ('ceo','cfo','cto')", name="ck_rol_invitacion"),
        Index("ix_invitaciones_abiertas", "correo", "usada_en"),
    )


class Sesion(Base):
    __tablename__ = "sesiones"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 del token: el token nunca se guarda
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    ip: Mapped[str | None] = mapped_column(String(64))
    agente_usuario: Mapped[str | None] = mapped_column(String(300))
    mfa_verificada_en: Mapped[datetime | None] = mapped_column(DateTime)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario: Mapped[Usuario] = relationship()


# ---------------------------------------------------------------------------
# Proveedores, contratos y cuentas
# ---------------------------------------------------------------------------
class Beneficiario(Base):
    __tablename__ = "beneficiarios"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    id_fiscal: Mapped[str] = mapped_column(String(40), index=True)
    tipo_id: Mapped[str | None] = mapped_column(String(12))
    id_valido: Mapped[bool | None] = mapped_column(Boolean)
    pais: Mapped[str] = mapped_column(String(2))
    tipo_persona: Mapped[str] = mapped_column(String(10))
    categoria: Mapped[str] = mapped_column(String(80))
    estado: Mapped[str] = mapped_column(String(12), default="activo")
    motivo_bloqueo: Mapped[str | None] = mapped_column(Text)
    contrato: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    contactos: Mapped[list[str]] = mapped_column(JSON, default=list)
    riel: Mapped[str] = mapped_column(String(12))
    moneda_recepcion: Mapped[str] = mapped_column(String(3))
    banco: Mapped[str] = mapped_column(String(120))
    cuenta_cifrada: Mapped[str] = mapped_column(Text)            # AES-256-GCM, ligada al id con AAD
    cuenta_ultimos4: Mapped[str] = mapped_column(String(4))
    titular_registrado: Mapped[str] = mapped_column(String(160))
    verificada_por: Mapped[str | None] = mapped_column(String(120))
    verificada_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    __table_args__ = (CheckConstraint("estado IN ('activo','bloqueado')", name="ck_estado_beneficiario"),)


class CambioCuenta(Base):
    """Un cambio de cuenta bancaria nunca se aplica solo: se verifica por un canal independiente."""
    __tablename__ = "cambios_cuenta"
    id: Mapped[int] = mapped_column(primary_key=True)
    beneficiario_id: Mapped[str] = mapped_column(ForeignKey("beneficiarios.id"), index=True)
    factura_id: Mapped[str | None] = mapped_column(String(12))
    banco_nuevo: Mapped[str] = mapped_column(String(120))
    cuenta_nueva_cifrada: Mapped[str] = mapped_column(Text)
    ultimos4_nuevos: Mapped[str] = mapped_column(String(4))
    origen: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    solicitada_por: Mapped[str] = mapped_column(String(120))
    verificada_por: Mapped[str | None] = mapped_column(String(120))
    metodo_verificacion: Mapped[str | None] = mapped_column(String(200))
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (CheckConstraint("estado IN ('pendiente','aprobado','rechazado')", name="ck_estado_cambio"),)


class VersionReglas(Base):
    __tablename__ = "reglas_versiones"
    version: Mapped[int] = mapped_column(primary_key=True)
    parametros: Mapped[dict[str, Any]] = mapped_column(JSON)
    creada_por: Mapped[str] = mapped_column(String(120))
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    motivo: Mapped[str] = mapped_column(Text, default="")
    cambios: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ---------------------------------------------------------------------------
# Facturas, decisiones y aprobaciones
# ---------------------------------------------------------------------------
class Factura(Base):
    __tablename__ = "facturas"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    archivo: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(12))
    origen: Mapped[str] = mapped_column(String(20), default="carga")     # set | sorpresa | carga | simulador
    ruta_archivo: Mapped[str | None] = mapped_column(String(300))
    hash_documento: Mapped[str] = mapped_column(String(64), index=True)
    hashes: Mapped[list[str]] = mapped_column(JSON, default=list)
    recibida_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    cargada_por: Mapped[str] = mapped_column(String(120), default="Agente Kauta")
    extraccion: Mapped[dict[str, Any]] = mapped_column(JSON)
    texto: Mapped[str] = mapped_column(Text, default="")
    metodo_lectura: Mapped[str] = mapped_column(String(20))
    modelo: Mapped[str] = mapped_column(String(120))
    beneficiario_id: Mapped[str | None] = mapped_column(ForeignKey("beneficiarios.id"), index=True)
    beneficiario_nombre: Mapped[str] = mapped_column(String(160))
    beneficiario_clave: Mapped[str] = mapped_column(String(80), index=True)
    numero: Mapped[str | None] = mapped_column(String(60))
    id_fiscal_unico: Mapped[str | None] = mapped_column(String(120), index=True)
    monto: Mapped[Decimal | None] = mapped_column(DINERO)
    moneda: Mapped[str | None] = mapped_column(String(3))
    monto_usd: Mapped[Decimal | None] = mapped_column(DINERO)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    fecha_vencimiento: Mapped[str | None] = mapped_column(String(10))
    decision: Mapped[str] = mapped_column(String(10))
    decision_inicial: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12), index=True)
    motivo: Mapped[str] = mapped_column(Text)
    motivo_inicial: Mapped[str] = mapped_column(Text)
    reglas: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    reglas_iniciales: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    version_reglas: Mapped[int] = mapped_column(Integer)
    aprobaciones_requeridas: Mapped[int] = mapped_column(Integer, default=0)
    # Quien cambió reglas o datos y provocó una reevaluación no puede ser la firma única de la factura
    excluir_firmante: Mapped[str | None] = mapped_column(String(160), nullable=True, default=None)
    # Cuándo llegó a un estado final (pagada, frenada o rechazada); lo fija un evento de SQLAlchemy
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    aprobaciones: Mapped[list["Aprobacion"]] = relationship(back_populates="factura", order_by="Aprobacion.id")
    __table_args__ = (
        CheckConstraint("decision IN ('pagar','frenar','escalar')", name="ck_decision"),
        CheckConstraint("estado IN ('pagada','frenada','pendiente','rechazada','devuelta')", name="ck_estado_factura"),
    )


class Aprobacion(Base):
    """Cada aprobación queda firmada (HMAC) sobre los datos exactos que la persona vio."""
    __tablename__ = "aprobaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[str] = mapped_column(ForeignKey("facturas.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    nivel: Mapped[int] = mapped_column(Integer)
    accion: Mapped[str] = mapped_column(String(10))
    comentario: Mapped[str] = mapped_column(Text, default="")
    correcciones: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reglas_revisadas: Mapped[list[str]] = mapped_column(JSON, default=list)
    datos_firmados: Mapped[dict[str, Any]] = mapped_column(JSON)
    firma: Mapped[str] = mapped_column(String(64))
    con_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    factura: Mapped[Factura] = relationship(back_populates="aprobaciones")
    __table_args__ = (UniqueConstraint("factura_id", "usuario_id", name="ux_una_aprobacion_por_persona"),
                      CheckConstraint("accion IN ('aprobar','rechazar')", name="ck_accion"))


# ---------------------------------------------------------------------------
# Libro de costos: cuánto cuesta leer, revisar, pagar y alojar cada factura (FinOps)
# ---------------------------------------------------------------------------
FUENTES_COSTO = ("lectura_xml", "lectura_texto", "lectura_ocr", "lectura_ia", "revision_humana",
                 "pago_comision", "pago_cambio", "infraestructura")


class EventoCosto(Base):
    """Un costo con su origen. La clave (fuente, origen_id) impide cobrar dos veces el mismo intento.

    El importe se guarda en milmillonésimas de USD; NULL significa costo desconocido (nunca cero).
    Se escribe en la misma transacción que la acción que lo causa (lectura, firma o pago).
    """
    __tablename__ = "eventos_costo"
    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[str | None] = mapped_column(ForeignKey("facturas.id"), index=True, nullable=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    fuente: Mapped[str] = mapped_column(String(20))
    origen_id: Mapped[str] = mapped_column(String(120))
    persona: Mapped[str | None] = mapped_column(String(160))
    importe_nano_usd: Mapped[int | None] = mapped_column(Numeric(24, 0), nullable=True)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer)
    tokens_cache: Mapped[int | None] = mapped_column(Integer)
    tokens_salida: Mapped[int | None] = mapped_column(Integer)
    latencia_ms: Mapped[int | None] = mapped_column(Integer)
    paginas: Mapped[int | None] = mapped_column(Integer)
    minutos: Mapped[float | None] = mapped_column(Numeric(8, 2))
    detalle: Mapped[str] = mapped_column(String(200), default="")
    tarifa_version: Mapped[int] = mapped_column(Integer)
    simulado: Mapped[bool] = mapped_column(Boolean, default=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    __table_args__ = (UniqueConstraint("fuente", "origen_id", name="ux_costo_una_vez"),
                      CheckConstraint("fuente IN ('" + "','".join(FUENTES_COSTO) + "')", name="ck_fuente_costo"))


# ---------------------------------------------------------------------------
# Wallet: libro mayor de doble partida
# ---------------------------------------------------------------------------
class CuentaWallet(Base):
    __tablename__ = "wallet_cuentas"
    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(12))      # activo | externa | gasto
    moneda: Mapped[str] = mapped_column(String(3), default="USD")
    descripcion: Mapped[str] = mapped_column(Text, default="")


class Asiento(Base):
    __tablename__ = "wallet_asientos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    tipo: Mapped[str] = mapped_column(String(16))
    descripcion: Mapped[str] = mapped_column(Text)
    referencia: Mapped[str | None] = mapped_column(String(40), index=True)
    periodo: Mapped[str] = mapped_column(String(7))
    movimientos: Mapped[list["Movimiento"]] = relationship(back_populates="asiento")


class Movimiento(Base):
    __tablename__ = "wallet_movimientos"
    id: Mapped[int] = mapped_column(primary_key=True)
    asiento_id: Mapped[int] = mapped_column(ForeignKey("wallet_asientos.id"), index=True)
    cuenta: Mapped[str] = mapped_column(ForeignKey("wallet_cuentas.codigo"), index=True)
    debito: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    credito: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    asiento: Mapped[Asiento] = relationship(back_populates="movimientos")
    __table_args__ = (CheckConstraint("debito >= 0 AND credito >= 0 AND (debito = 0 OR credito = 0)", name="ck_partida"),)


class Pago(Base):
    __tablename__ = "pagos"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    factura_id: Mapped[str] = mapped_column(ForeignKey("facturas.id"), index=True)
    beneficiario_id: Mapped[str] = mapped_column(ForeignKey("beneficiarios.id"))
    beneficiario_nombre: Mapped[str] = mapped_column(String(160))
    riel: Mapped[str] = mapped_column(String(12))
    monto_factura: Mapped[Decimal] = mapped_column(DINERO)
    moneda_factura: Mapped[str] = mapped_column(String(3))
    monto_usd: Mapped[Decimal] = mapped_column(DINERO)
    moneda_destino: Mapped[str] = mapped_column(String(3))
    monto_destino: Mapped[Decimal] = mapped_column(DINERO)
    tasa_referencia: Mapped[Decimal] = mapped_column(TASA)
    tasa_aplicada: Mapped[Decimal] = mapped_column(TASA)
    comision_usd: Mapped[Decimal] = mapped_column(DINERO)
    costo_fx_usd: Mapped[Decimal] = mapped_column(DINERO)
    cuenta_ultimos4: Mapped[str] = mapped_column(String(4))
    titular_confirmado: Mapped[str | None] = mapped_column(String(160))
    referencia: Mapped[str] = mapped_column(String(60))
    estado: Mapped[str] = mapped_column(String(12))
    clave_idempotencia: Mapped[str] = mapped_column(String(80), unique=True)
    datos_firmados: Mapped[dict[str, Any]] = mapped_column(JSON)
    firma: Mapped[str] = mapped_column(String(64))
    linea_tiempo: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    motivo_devolucion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    liquidado_en: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (
        CheckConstraint("estado IN ('reservado','enviado','liquidado','devuelto')", name="ck_estado_pago"),
        CheckConstraint("monto_usd > 0", name="ck_monto_positivo"),
        # Defensa en profundidad: la base de datos impide dos pagos vivos para la misma factura
        Index("ux_un_pago_vivo_por_factura", "factura_id", unique=True,
              sqlite_where=text("estado != 'devuelto'"), postgresql_where=text("estado <> 'devuelto'")),
    )


# ---------------------------------------------------------------------------
# Auditoría e idempotencia
# ---------------------------------------------------------------------------
class EventoAuditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[str] = mapped_column(String(32))
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[str | None] = mapped_column(String(40), index=True)
    resumen: Mapped[str] = mapped_column(Text)
    datos: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    hash_anterior: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class ClaveIdempotencia(Base):
    __tablename__ = "idempotencia"
    clave: Mapped[str] = mapped_column(String(80), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer)
    ruta: Mapped[str] = mapped_column(String(120))
    hash_solicitud: Mapped[str] = mapped_column(String(64))
    respuesta: Mapped[dict[str, Any]] = mapped_column(JSON)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)


# Cuándo una factura queda resuelta: se fija al pasar a un estado final y se borra si vuelve a uno abierto
ESTADOS_FINALES = ("pagada", "frenada", "rechazada")


@event.listens_for(Factura.estado, "set")
def _marcar_resuelta(factura: Factura, valor: str, _anterior: Any, _iniciador: Any) -> None:
    if valor in ESTADOS_FINALES:
        if factura.resuelta_en is None:
            factura.resuelta_en = ahora()
    else:
        factura.resuelta_en = None
