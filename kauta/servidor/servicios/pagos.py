"""
Simulador de pagos: rieles, cambio de moneda, comisiones, confirmación de titular y liquidación.

Ningún pago sale de verdad: todo ocurre en el libro mayor de la wallet con referencias simuladas.
Aun así, cada pago pasa por los mismos controles que tendría en producción:

  1. Re-verificación de las firmas de TODAS las aprobaciones humanas (si el monto, la cuenta o el
     documento cambiaron después de aprobar, el pago se bloquea).
  2. Confirmación de titular (CoP): el nombre que devuelve el directorio de la cuenta debe ser el
     del beneficiario registrado.
  3. Doble verificación de saldo: la regla R12 del motor y el saldo real de la sub-wallet.
  4. Idempotencia: una clave única por pago; reintentar nunca paga dos veces.
  5. La base de datos impide dos pagos vivos para la misma factura (índice único parcial).
"""
from __future__ import annotations

import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kauta.motor import fmt_dinero
from kauta.normalizacion import clave_nombre

from ..modelos import Aprobacion, Beneficiario, Factura, Pago, ahora
from ..seguridad import firma
from ..seguridad.cifrado import descifrar
from . import auditoria, costos, wallet

CENT = Decimal("0.01")

RIELES: dict[str, dict[str, Any]] = {
    "ACH": {"nombre": "ACH", "region": "Estados Unidos", "moneda": "USD", "comision": "0.50", "spread": "0",
            "liquidacion": "Mismo día (same-day ACH) o día hábil siguiente", "segundos": 6,
            "disponibilidad": "Días hábiles, por ventanas de corte", "referencia": "Número de rastreo (trace number)",
            "requisitos": "Routing ABA de 9 dígitos con dígito de control y número de cuenta",
            "devolucion": "ACH R03: no existe la cuenta o no se pudo ubicar"},
    "WIRE": {"nombre": "Wire doméstico (Fedwire)", "region": "Estados Unidos", "moneda": "USD", "comision": "15.00",
             "spread": "0", "liquidacion": "Minutos, en horario de Fedwire", "segundos": 4, "disponibilidad": "Días hábiles",
             "referencia": "IMAD", "requisitos": "Routing ABA y número de cuenta",
             "devolucion": "Wire devuelto por el banco receptor: cuenta cerrada"},
    "SWIFT": {"nombre": "Transferencia internacional SWIFT", "region": "Internacional", "moneda": "USD", "comision": "25.00",
              "spread": "0", "liquidacion": "1 a 2 días hábiles (seguimiento SWIFT gpi)", "segundos": 8,
              "disponibilidad": "Días hábiles", "referencia": "UETR (identificador único de extremo a extremo)",
              "requisitos": "Código SWIFT/BIC del banco y cuenta del beneficiario",
              "devolucion": "MT103 rechazado por el banco intermediario: datos del beneficiario incompletos"},
    "SPEI": {"nombre": "SPEI", "region": "México", "moneda": "MXN", "comision": "0.30", "spread": "0.004",
             "liquidacion": "Segundos, 24/7", "segundos": 3, "disponibilidad": "24/7", "referencia": "Clave de rastreo",
             "requisitos": "CLABE de 18 dígitos con dígito de control",
             "devolucion": "SPEI devuelto: la CLABE no pertenece al titular"},
    "BREB": {"nombre": "Bre-B", "region": "Colombia", "moneda": "COP", "comision": "0.00", "spread": "0.005",
             "liquidacion": "Segundos, 24/7", "segundos": 3, "disponibilidad": "24/7",
             "referencia": "Identificador de extremo a extremo", "requisitos": "Llave Bre-B (celular, documento, correo o alfanumérica)",
             "devolucion": "Bre-B rechazado: la llave no existe en el directorio"},
    "ACH_CO": {"nombre": "Transferencia ACH Colombia", "region": "Colombia", "moneda": "COP", "comision": "0.40",
               "spread": "0.005", "liquidacion": "Mismo día, por ciclos de compensación", "segundos": 5,
               "disponibilidad": "Días hábiles", "referencia": "Número de transacción",
               "requisitos": "Banco, tipo y número de cuenta", "devolucion": "ACH Colombia: cuenta inactiva"},
    "PIX": {"nombre": "Pix", "region": "Brasil", "moneda": "BRL", "comision": "0.00", "spread": "0.005",
            "liquidacion": "Segundos, 24/7", "segundos": 3, "disponibilidad": "24/7", "referencia": "EndToEndId",
            "requisitos": "Chave Pix (CPF/CNPJ, correo, teléfono o aleatoria)", "devolucion": "Pix devuelto (MED)"},
    "USDC": {"nombre": "Stablecoin USDC (alternativa)", "region": "Global", "moneda": "USD", "comision": "0.05",
             "spread": "0", "liquidacion": "Minutos, 24/7", "segundos": 4, "disponibilidad": "24/7",
             "referencia": "Hash de la transacción", "requisitos": "Dirección de billetera verificada del beneficiario",
             "devolucion": "Transacción revertida: dirección no verificada"},
}


def _referencia(riel: str, rnd: random.Random) -> str:
    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
    al = lambda n, abc="ABCDEFGHJKLMNPQRSTUVWXYZ23456789": "".join(rnd.choice(abc) for _ in range(n))
    if riel == "ACH":
        return "13" + "".join(rnd.choice("0123456789") for _ in range(13))
    if riel == "WIRE":
        return f"{hoy}KAUT{al(4)}{rnd.randint(0, 999999):06d}"
    if riel == "SWIFT":
        return str(uuid.UUID(int=rnd.getrandbits(128), version=4))
    if riel == "SPEI":
        return f"KAUTA{hoy}{al(8)}"
    if riel == "BREB":
        return f"E{hoy}KAUTA{al(19)}"
    if riel == "PIX":
        return f"E99999999{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}{al(11)}"
    if riel == "USDC":
        return "0x" + "".join(rnd.choice("0123456789abcdef") for _ in range(64))
    return f"CO{hoy}{rnd.randint(0, 99999999):08d}"


def cotizar(bd_reglas: dict[str, Any], factura: Factura, ben: Beneficiario, riel: str) -> dict[str, Decimal]:
    """Calcula lo que recibe el beneficiario y lo que cuesta, en USD, enviarlo por el riel."""
    info = RIELES[riel]
    tasas = {k: Decimal(str(v)) for k, v in bd_reglas.get("tasas_cambio", {}).items() if not k.startswith("_")}
    monto_usd = Decimal(factura.monto_usd)
    destino = ben.moneda_recepcion
    ref = tasas.get(destino, Decimal("1"))
    spread = Decimal(info["spread"]) if destino != "USD" else Decimal("0")
    if factura.moneda == destino:
        monto_destino = Decimal(factura.monto)
    else:
        monto_destino = (monto_usd * ref).quantize(CENT, ROUND_HALF_UP)
    aplicada = (ref * (1 - spread)).quantize(Decimal("0.000001"))
    costo_real = (monto_destino / aplicada).quantize(CENT, ROUND_HALF_UP) if destino != "USD" else monto_usd
    return {"monto_destino": monto_destino, "tasa_referencia": ref, "tasa_aplicada": aplicada,
            "costo_fx_usd": max(Decimal("0"), costo_real - monto_usd).quantize(CENT), "comision_usd": Decimal(info["comision"])}


def confirmar_titular(ben: Beneficiario) -> tuple[bool, str]:
    """Confirmación de titular (Confirmation of Payee): el directorio devuelve el nombre de la cuenta."""
    ok = clave_nombre(ben.titular_registrado) == clave_nombre(ben.nombre)
    return ok, ben.titular_registrado


def datos_aprobacion(f: Factura, ben_id: str | None, cuenta4: str, usuario_id: int, nivel: int, accion: str,
                     ts: str) -> dict[str, Any]:
    return {"factura_id": f.id, "beneficiario_id": ben_id, "monto": str(f.monto), "moneda": f.moneda,
            "monto_usd": str(f.monto_usd), "cuenta_ultimos4": cuenta4, "hash_documento": f.hash_documento,
            "version_reglas": f.version_reglas, "usuario_id": usuario_id, "nivel": nivel, "accion": accion, "ts": ts}


def verificar_aprobaciones(bd: Session, f: Factura, ben: Beneficiario) -> list[str]:
    """Recalcula cada firma con los datos ACTUALES de la factura. Devuelve los problemas encontrados."""
    problemas = []
    for a in bd.execute(select(Aprobacion).where(Aprobacion.factura_id == f.id, Aprobacion.accion == "aprobar")).scalars():
        actual = datos_aprobacion(f, ben.id, ben.cuenta_ultimos4, a.usuario_id, a.nivel, "aprobar", a.datos_firmados.get("ts"))
        if not firma.verificar(actual, a.firma):
            problemas.append(f"La aprobación de {a.usuario_nombre} ya no coincide con los datos actuales "
                             "(monto, cuenta o documento cambiaron después de aprobar).")
    return problemas


def nuevo_id(bd: Session) -> str:
    n = bd.execute(select(func.count()).select_from(Pago)).scalar_one() + 1
    return f"PAG-{n:06d}"


def crear_y_ejecutar(bd: Session, f: Factura, reglas: dict[str, Any], actor: str, forzar: str | None = None,
                     riel: str | None = None, intento: int = 1) -> Pago:
    ben = bd.get(Beneficiario, f.beneficiario_id) if f.beneficiario_id else None
    if not ben or ben.estado != "activo":
        raise ValueError("Solo se paga a beneficiarios registrados y activos.")
    problemas = verificar_aprobaciones(bd, f, ben)
    if problemas:
        raise ValueError(problemas[0])
    riel = riel or ben.riel
    if riel not in RIELES:
        raise ValueError(f"Riel desconocido: {riel}.")
    cop_ok, titular = confirmar_titular(ben)
    if not cop_ok:
        raise ValueError(f"Confirmación de titular fallida: la cuenta está a nombre de «{titular}», no de «{ben.nombre}».")
    disponible = wallet.saldo(bd, "cxp")
    monto_usd = Decimal(f.monto_usd).quantize(CENT)
    if monto_usd > disponible:
        raise ValueError(f"La sub-wallet de cuentas por pagar tiene {fmt_dinero(disponible)}; el pago requiere {fmt_dinero(monto_usd)}.")
    clave = f"pago:{f.id}:{f.hash_documento[:16]}:{intento}"
    existente = bd.execute(select(Pago).where(Pago.clave_idempotencia == clave)).scalar_one_or_none()
    if existente:
        return existente  # idempotencia: el mismo intento nunca crea un segundo pago

    c = cotizar(reglas, f, ben, riel)
    rnd = random.Random(secrets.randbits(64))
    pid = nuevo_id(bd)
    referencia = _referencia(riel, rnd)
    cuenta_completa = descifrar(ben.cuenta_cifrada, aad=f"cuenta:{ben.id}")
    instruccion = {"pago": pid, "factura": f.id, "beneficiario": ben.id, "riel": riel, "monto_usd": str(monto_usd),
                   "moneda_destino": ben.moneda_recepcion, "monto_destino": str(c["monto_destino"]),
                   "cuenta_ultimos4": ben.cuenta_ultimos4, "hash_cuenta": firma.huella({"c": cuenta_completa}),
                   "clave_idempotencia": clave}
    t0 = ahora()
    info = RIELES[riel]
    seg = info["segundos"]
    pasos = [
        {"paso": "creado", "titulo": "Orden de pago creada y firmada", "detalle": f"Firma HMAC {firma.huella(instruccion)} · clave de idempotencia {clave}", "t": 0},
        {"paso": "verificado", "titulo": "Controles previos superados", "detalle": f"Titular confirmado: {titular} · saldo suficiente · firmas de aprobación válidas", "t": 0.4},
        {"paso": "reservado", "titulo": "Fondos reservados en la wallet", "detalle": f"{fmt_dinero(monto_usd)} pasan de la sub-wallet de pagos a reservas", "t": 0.8},
        {"paso": "enviado", "titulo": f"Enviado por {info['nombre']}", "detalle": f"{info['referencia']}: {referencia}", "t": 1.4},
    ]
    p = Pago(id=pid, factura_id=f.id, beneficiario_id=ben.id, beneficiario_nombre=ben.nombre, riel=riel,
             monto_factura=Decimal(f.monto), moneda_factura=f.moneda, monto_usd=monto_usd, moneda_destino=ben.moneda_recepcion,
             monto_destino=c["monto_destino"], tasa_referencia=c["tasa_referencia"], tasa_aplicada=c["tasa_aplicada"],
             comision_usd=c["comision_usd"], costo_fx_usd=c["costo_fx_usd"], cuenta_ultimos4=ben.cuenta_ultimos4,
             titular_confirmado=titular, referencia=referencia, estado="enviado", clave_idempotencia=clave,
             datos_firmados=instruccion, firma=firma.firmar(instruccion), creado_en=t0)
    bd.add(p)
    bd.flush()
    costos.registrar_pago(bd, f, p)  # dentro del savepoint del pago: si el pago se revierte, su costo también
    per = f.periodo
    wallet.transferir(bd, "reserva", f"Reserva para {pid} · {f.id} · {ben.nombre}", pid, per, "cxp", "reservas", monto_usd)
    wallet.transferir(bd, "envio", f"Envío por {info['nombre']} · {pid}", pid, per, "reservas", "transito", monto_usd)
    if c["comision_usd"] > 0:
        wallet.transferir(bd, "comision", f"Comisión {info['nombre']} · {pid}", pid, per, "operativa", "comisiones", c["comision_usd"])
    if c["costo_fx_usd"] > 0:
        wallet.transferir(bd, "fx", f"Costo cambiario USD→{ben.moneda_recepcion} · {pid}", pid, per, "operativa", "costos_fx", c["costo_fx_usd"])

    if forzar == "devuelto":
        motivo = info["devolucion"]
        wallet.transferir(bd, "devolucion", f"Devolución de {pid}: {motivo}", pid, per, "transito", "cxp", monto_usd)
        p.estado, p.motivo_devolucion = "devuelto", motivo
        f.estado = "devuelta"
        f.motivo = (f"Devuelta por el riel · {motivo}. Los {fmt_dinero(monto_usd)} volvieron a la sub-wallet; "
                    "la factura queda para revisión de tesorería (los datos bancarios deben verificarse).")
        pasos.append({"paso": "devuelto", "titulo": "Devuelto por el banco receptor", "detalle": motivo + " · fondos reintegrados", "t": 1.4 + seg})
        auditoria.registrar(bd, "pago.devuelto", "Riel de pagos (simulado)", "pago", pid, f"{pid} devuelto: {motivo}",
                            {"factura": f.id, "monto_usd": str(monto_usd)})
    else:
        wallet.transferir(bd, "liquidacion", f"Liquidación {pid} · {ben.nombre}", pid, per, "transito", "proveedores", monto_usd)
        p.estado, p.liquidado_en = "liquidado", t0 + timedelta(seconds=seg)
        pasos.append({"paso": "liquidado", "titulo": "Liquidado: el beneficiario recibió el dinero",
                      "detalle": f"{fmt_dinero(c['monto_destino'], ben.moneda_recepcion)} en la cuenta ···{ben.cuenta_ultimos4} · {info['liquidacion']}",
                      "t": 1.4 + seg})
    p.linea_tiempo = pasos
    auditoria.registrar(bd, "pago.creado", actor, "pago", pid,
                        f"{pid}: {fmt_dinero(monto_usd)} a {ben.nombre} por {info['nombre']} ({p.estado})",
                        {"factura": f.id, "riel": riel, "referencia": referencia, "firma": p.firma[:16],
                         "comision_usd": str(c["comision_usd"]), "costo_fx_usd": str(c["costo_fx_usd"])})
    return p


def a_dict(p: Pago) -> dict[str, Any]:
    info = RIELES.get(p.riel, {})
    return {"id": p.id, "factura_id": p.factura_id, "beneficiario_id": p.beneficiario_id, "beneficiario": p.beneficiario_nombre,
            "riel": p.riel, "riel_nombre": info.get("nombre", p.riel), "liquidacion": info.get("liquidacion"),
            "monto_factura": float(p.monto_factura), "moneda_factura": p.moneda_factura, "monto_usd": float(p.monto_usd),
            "moneda_destino": p.moneda_destino, "monto_destino": float(p.monto_destino),
            "tasa_referencia": float(p.tasa_referencia), "tasa_aplicada": float(p.tasa_aplicada),
            "comision_usd": float(p.comision_usd), "costo_fx_usd": float(p.costo_fx_usd),
            "costo_total_usd": float(p.monto_usd + p.comision_usd + p.costo_fx_usd),
            "cuenta": f"···{p.cuenta_ultimos4}", "titular": p.titular_confirmado, "referencia": p.referencia,
            "estado": p.estado, "firma": p.firma[:16], "clave_idempotencia": p.clave_idempotencia,
            "linea_tiempo": p.linea_tiempo, "motivo_devolucion": p.motivo_devolucion,
            "creado_en": p.creado_en.isoformat() + "Z", "liquidado_en": p.liquidado_en.isoformat() + "Z" if p.liquidado_en else None}
