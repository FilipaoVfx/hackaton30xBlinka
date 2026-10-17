"""
Carga inicial de la demo: empresa, usuarios por rol, proveedores con datos de pago ficticios
(validados con su dígito de control), reglas v1, wallet fondeada y, opcionalmente, las 20 facturas del set.
TODOS LOS DATOS SON FICTICIOS.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from kauta.normalizacion import validar_aba, validar_clabe, validar_id_fiscal

from ..config import CONFIG, RAIZ
from ..db import Base, motor_bd
from ..modelos import (Aprobacion, Asiento, Beneficiario, CambioCuenta, ClaveIdempotencia, CuentaWallet, EventoAuditoria, EventoCosto,
                       Factura, Movimiento, Organizacion, Pago, Sesion, Usuario, VersionReglas)
from ..seguridad.cifrado import cifrar
from ..seguridad.contrasenas import hashear, problemas_politica
from . import BLOQUEO, agente, auditoria, wallet

DATA = RAIZ / "data"
CONTRASENA_DEMO = "Kauta-30X-demo-2026"
USUARIOS_DEMO = [
    ("carlos.rivera@brisamar.example", "Carlos Rivera", "CFO", "cfo"),
    ("mariana.torres@brisamar.example", "Mariana Torres", "CEO", "ceo"),
    ("tomas.herrera@brisamar.example", "Tomás Herrera", "CTO", "cto"),
]
# riel, moneda en que recibe, banco (todo simulado)
PAGO = {
    "B01": ("SWIFT", "USD", "Banco Cóndor (simulado) · SWIFT CNDRCOBB"),
    "B02": ("BREB", "COP", "Banco del Pacífico Sur (simulado) · llave Bre-B @carolinamendez"),
    "B03": ("ACH", "USD", "Lone Star Community Bank (simulado)"),
    "B04": ("SPEI", "MXN", "BancoMar (simulado)"),
    "B05": ("SWIFT", "USD", "Banco Austral (simulado) · SWIFT AUSTARBA"),
    "B06": ("SPEI", "MXN", "Banco Jade (simulado)"),
    "B07": ("WIRE", "USD", "Hudson Mutual Bank (simulado)"),
    "B08": ("BREB", "COP", "Banco Cóndor (simulado) · llave Bre-B @soportenexo"),
    "B09": ("SPEI", "MXN", "Banco Jade (simulado)"),
    "B10": ("BREB", "COP", "Banco del Pacífico Sur (simulado) · llave Bre-B @andresrojas"),
    "B11": ("SWIFT", "USD", "Banco Cóndor (simulado) · SWIFT CNDRCOBB"),
    "B12": ("ACH_CO", "COP", "Banco Cóndor (simulado) · cuenta de ahorros"),
    "B13": ("SWIFT", "USD", "Banco del Pacífico Sur (simulado) · SWIFT PSURCOBB"),
    "B14": ("ACH_CO", "COP", "Banco del Pacífico Sur (simulado) · cuenta corriente"),
    "X01": ("ACH", "USD", "Gulf Coast Bank (simulado)"),
}


def cuenta_ficticia(riel: str, ultimos4: str, rnd: random.Random) -> tuple[str, str]:
    """Número completo ficticio que termina en los 4 dígitos registrados y pasa su validación de formato."""
    d = lambda n: "".join(rnd.choice("0123456789") for _ in range(n))
    if riel in ("ACH", "WIRE"):
        base = "13" + d(6)  # el prefijo 13 no lo asigna la ABA: routing válido en formato y ficticio
        suma = sum(int(x) * p for x, p in zip(base, (3, 7, 1, 3, 7, 1, 3, 7)))
        routing = base + str((10 - suma % 10) % 10)
        assert validar_aba(routing).valido
        return f"ABA {routing} · cuenta {d(6)}{ultimos4}", "ABA con dígito de control válido"
    if riel == "SPEI":
        for _ in range(10000):  # 999 = banco inexistente; se busca la cuenta cuyo control deje la terminación registrada
            k = "999180" + d(8) + ultimos4[:3]
            suma = sum((int(x) * p) % 10 for x, p in zip(k, (3, 7, 1) * 6))
            if str((10 - suma % 10) % 10) == ultimos4[3]:
                assert validar_clabe(k + ultimos4[3]).valido
                return f"CLABE {k}{ultimos4[3]}", "CLABE de 18 dígitos con dígito de control válido"
    if riel == "BREB":
        return f"Cuenta de ahorros {d(6)}{ultimos4} (resuelta por la llave Bre-B)", "Llave Bre-B resuelta en el directorio"
    if riel == "SWIFT":
        return f"Cuenta {d(6)}{ultimos4}", "Código SWIFT/BIC con formato ISO 9362 válido"
    return f"Cuenta {d(7)}{ultimos4}", "Cuenta local"


def _usuarios(bd: Session) -> None:
    if bd.execute(select(Usuario)).first():
        return
    if not CONFIG.demo:
        return  # en producción los usuarios se crean con el proveedor de identidad, no con semillas
    h = hashear(CONTRASENA_DEMO)
    for correo, nombre, cargo, rol in USUARIOS_DEMO:
        if problemas_politica(CONTRASENA_DEMO, correo):
            raise RuntimeError(f"La contraseña de la demo no cumple la política: {problemas_politica(CONTRASENA_DEMO, correo)}")
        bd.add(Usuario(correo=correo, nombre=nombre, cargo=cargo, rol=rol, hash_contrasena=h))


def _invitacion_demo(bd: Session) -> None:
    """Una invitación pendiente de ejemplo, para que «Personas y roles» muestre el flujo completo."""
    from ..modelos import Invitacion
    from . import usuarios as serv_usuarios
    if not CONFIG.demo or bd.execute(select(Invitacion)).first():
        return
    bd.add(Invitacion(correo="daniel.osorio@brisamar.example", nombre="Daniel Osorio", cargo="Controller financiero",
                      rol="cfo", hash_codigo=hashear(serv_usuarios.generar_codigo()), prefijo="KAUD",
                      creada_por="Tomás Herrera (CTO)",
                      creada_en=datetime.now(timezone.utc), expira_en=datetime.now(timezone.utc) + timedelta(days=5)))


def _negocio(bd: Session, con_set: bool) -> None:
    empresa = json.loads((DATA / "empresa.json").read_text(encoding="utf-8"))
    if not bd.get(Organizacion, 1):
        bd.add(Organizacion(id=1, nombre=empresa["nombre"], id_fiscal=empresa["id_fiscal"], datos=empresa))
    rnd = random.Random(30)
    for b in json.loads((DATA / "beneficiarios.json").read_text(encoding="utf-8")):
        riel, moneda, banco = PAGO[b["id"]]
        cuenta, nota = cuenta_ficticia(riel, b["cuenta_registrada"], rnd)
        v = validar_id_fiscal(b["id_fiscal"], b["pais"])
        bd.add(Beneficiario(id=b["id"], nombre=b["nombre"], id_fiscal=b["id_fiscal"], tipo_id=v.tipo, id_valido=v.valido,
                            pais=b["pais"], tipo_persona=b["tipo_persona"], categoria=b["categoria"], estado=b["estado"],
                            motivo_bloqueo=b["motivo_bloqueo"], contrato=b["contrato"], contactos=b["contactos"], riel=riel,
                            moneda_recepcion=moneda, banco=f"{banco} · {nota}",
                            cuenta_cifrada=cifrar(cuenta, aad=f"cuenta:{b['id']}"), cuenta_ultimos4=b["cuenta_registrada"],
                            titular_registrado=b["nombre"], verificada_por="Alta inicial del proveedor (documentos y llamada)",
                            verificada_en=datetime(2026, 9, 1, 15, 0)))
    reglas = json.loads((DATA / "reglas.json").read_text(encoding="utf-8"))
    bd.add(VersionReglas(version=1, parametros={k: v for k, v in reglas.items() if k != "version"},
                         creada_por="Mariana Torres (Finance Lead)", motivo="Política de pagos inicial de octubre de 2026"))
    wallet.crear_cuentas(bd)
    per = reglas["periodo_actual"]
    wallet.transferir(bd, "fondeo", "Depósito inicial simulado en la cuenta operativa", "FONDEO-0", per, "fondeo", "operativa", Decimal("120000"))
    wallet.transferir(bd, "fondeo", f"Fondeo de la sub-wallet de cuentas por pagar para {per}", f"FONDEO-{per}", per, "operativa", "cxp",
                      Decimal(str(reglas["presupuesto_periodo_usd"])))
    bd.flush()
    auditoria.registrar(bd, "demo.inicio", "Sistema", "organizacion", "1",
                        f"Demo iniciada: {empresa['nombre']}, reglas v1, sub-wallet fondeada con USD {reglas['presupuesto_periodo_usd']:,}.", {})
    bd.commit()
    if con_set:
        ref = json.loads((DATA / "referencia_extracciones.json").read_text(encoding="utf-8"))
        for p in sorted((DATA / "facturas").iterdir()):
            if p.is_file() and not p.name.startswith("."):
                f = agente.procesar_archivo(bd, p.name, p.read_bytes(), "set", "Agente Kauta", "buzon@brisamar.example")
                recibida = ref.get(p.name, {}).get("recibida")
                if recibida:  # hora de Bogotá (UTC-5) guardada en UTC
                    f.recibida_en = datetime.fromisoformat(recibida) + timedelta(hours=5)
        bd.commit()


def iniciar(bd: Session, con_set: bool = True) -> None:
    Base.metadata.create_all(motor_bd)
    _usuarios(bd)
    _invitacion_demo(bd)
    bd.commit()
    if not bd.get(Organizacion, 1):
        _negocio(bd, con_set)


TABLAS_NEGOCIO = [EventoCosto, ClaveIdempotencia, Movimiento, Asiento, Pago, Aprobacion, CambioCuenta, Factura, Beneficiario,
                  VersionReglas, CuentaWallet, EventoAuditoria, Organizacion]


def restablecer(bd: Session, con_set: bool, actor: str) -> None:
    """Vuelve la demo al estado inicial. Conserva usuarios y sesiones."""
    with BLOQUEO:
        for t in TABLAS_NEGOCIO:
            bd.execute(delete(t))
        bd.commit()
        _negocio(bd, con_set)
        auditoria.registrar(bd, "demo.restablecida", actor, "organizacion", "1",
                            "La demo se restableció " + ("con las 20 facturas del set." if con_set else "sin facturas."), {})
        bd.commit()


def preparar_recorrido(bd: Session) -> None:
    """Prepara el ensayo sin cambiar el set de referencia ni el motor de reglas.

    Es un estado opcional de demo: amplía el presupuesto de octubre de forma
    auditada y registra la primera firma de F10 por la ruta normal del agente.
    Las facturas finales conservan su decisión original. Restablecer sin esta
    opción recupera el set oficial intacto.
    """
    if not CONFIG.demo:
        raise ValueError("El recorrido solo se prepara en modo demo.")
    with BLOQUEO:
        f = bd.get(Factura, "F10")
        if not f or f.estado != "pendiente" or f.aprobaciones:
            return
        actual = agente.reglas_vigentes(bd)
        presupuesto = Decimal(str(actual["presupuesto_periodo_usd"]))
        objetivo = max(presupuesto, Decimal("20000"))
        if objetivo > presupuesto:
            version = actual["version"] + 1
            parametros = {k: v for k, v in actual.items() if k != "version"}
            parametros["presupuesto_periodo_usd"] = float(objetivo)
            bd.add(VersionReglas(version=version, parametros=parametros,
                                creada_por="Preparación de demo", motivo="Presupuesto simulado para el recorrido F12 y F10.",
                                cambios={"presupuesto_periodo_usd": {"antes": float(presupuesto), "despues": float(objetivo)}}))
            wallet.transferir(bd, "fondeo", "Ajuste simulado para preparar el recorrido de demostración", "DEMO-RECORRIDO",
                              actual["periodo_actual"], "operativa", "cxp", objetivo - presupuesto)
            auditoria.registrar(bd, "demo.recorrido", "Preparación de demo", "reglas", str(version),
                                "Recorrido preparado: presupuesto simulado de USD 20.000; sin relajar reglas duras.", {})
            bd.commit()
        cfo = bd.execute(select(Usuario).where(Usuario.correo == "carlos.rivera@brisamar.example")).scalar_one()
        agente.aprobar(bd, "F10", cfo, "Primera firma simulada para el ensayo: contrato verificado; falta la firma del CEO.", None, False)
