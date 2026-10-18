"""Recepción de correo separada de la decisión financiera: un error de lectura no es un rechazo."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .modelos import ahora


class FuenteCorreo(Base):
    __tablename__ = "ingesta_correo_fuentes"
    cuenta: Mapped[str] = mapped_column(String(254), primary_key=True)
    desde: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    cursor: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ultima_consulta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ultimo_exito: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CorreoRecibido(Base):
    __tablename__ = "ingesta_correos"
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta: Mapped[str] = mapped_column(String(254), index=True)
    mensaje_id: Mapped[str] = mapped_column(String(100))
    hilo_id: Mapped[str] = mapped_column(String(100), default="")
    asunto: Mapped[str] = mapped_column(String(500), default="")
    remitente: Mapped[str] = mapped_column(String(500), default="")
    recibida_en: Mapped[datetime] = mapped_column(DateTime)
    ruta_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("cuenta", "mensaje_id", name="ux_correo_gmail"),)


class DocumentoRecibido(Base):
    __tablename__ = "ingesta_correo_documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    correo_id: Mapped[int] = mapped_column(ForeignKey("ingesta_correos.id"), index=True)
    parte: Mapped[str] = mapped_column(String(100))
    nombre: Mapped[str] = mapped_column(String(200))
    huella: Mapped[str] = mapped_column(String(64), index=True)
    ruta: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="recibido")
    motivo: Mapped[str] = mapped_column(Text, default="")
    factura_id: Mapped[str | None] = mapped_column(ForeignKey("facturas.id", ondelete="SET NULL"), nullable=True)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    __table_args__ = (UniqueConstraint("correo_id", "parte", name="ux_correo_parte"),)
