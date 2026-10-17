"""Wallet, pagos, rieles y comprobantes."""
from __future__ import annotations

import io
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from ..esquemas import FondearIn, ReintentarIn
from ..modelos import Asiento, Factura, Pago
from ..seguridad.sesiones import Contexto, requiere
from ..servicios import BLOQUEO, agente, auditoria, pagos, wallet
from .. import vistas

r = APIRouter(prefix="/api", tags=["Dinero"])


@r.get("/wallet")
def ver_wallet(ctx: Contexto = Depends(requiere("ver"))):
    reglas = agente.reglas_vigentes(ctx.bd)
    res = wallet.resumen(ctx.bd)
    asientos = ctx.bd.execute(select(Asiento).order_by(Asiento.id.desc()).limit(40)).scalars().all()
    from ..servicios.simulador import disponible_periodo
    periodos = []
    for per in wallet.periodos_fondeados(ctx.bd):
        disp = float(disponible_periodo(ctx.bd, reglas, per))
        periodos.append({"periodo": per, "presupuesto": reglas["presupuesto_periodo_usd"], "disponible": disp,
                         "pagado": round(reglas["presupuesto_periodo_usd"] - disp, 2)})
    res.update({
        "periodo": reglas["periodo_actual"], "presupuesto": reglas["presupuesto_periodo_usd"], "periodos": periodos,
        "libro": wallet.verificar_libro(ctx.bd),
        "asientos": [{"id": a.id, "fecha": vistas.iso(a.fecha), "tipo": a.tipo, "descripcion": a.descripcion,
                      "referencia": a.referencia,
                      "movimientos": [{"cuenta": m.cuenta, "debito": float(m.debito), "credito": float(m.credito)} for m in a.movimientos]}
                     for a in asientos],
    })
    return res


@r.post("/wallet/fondear")
def fondear(datos: FondearIn, ctx: Contexto = Depends(requiere("wallet.fondear"))):
    with BLOQUEO:
        reglas = agente.reglas_vigentes(ctx.bd)
        wallet.transferir(ctx.bd, "fondeo", f"Depósito simulado a la cuenta operativa por {ctx.actor}", "FONDEO",
                          reglas["periodo_actual"], "fondeo", "operativa", Decimal(str(datos.monto)))
        auditoria.registrar(ctx.bd, "wallet.fondeo", ctx.actor, "wallet", "operativa", f"Depósito simulado de USD {datos.monto:,.2f}.", {})
        ctx.bd.commit()
    return wallet.resumen(ctx.bd)


@r.get("/pagos")
def listar_pagos(ctx: Contexto = Depends(requiere("ver"))):
    return [pagos.a_dict(p) for p in ctx.bd.execute(select(Pago).order_by(Pago.creado_en.desc(), Pago.id.desc())).scalars()]


@r.get("/pagos/{pid}")
def ver_pago(pid: str, ctx: Contexto = Depends(requiere("ver"))):
    p = ctx.bd.get(Pago, pid)
    if not p:
        raise HTTPException(404, "Pago no encontrado.")
    return pagos.a_dict(p)


@r.post("/pagos/{pid}/reintentar")
def reintentar(pid: str, datos: ReintentarIn, ctx: Contexto = Depends(requiere("pagos.reintentar"))):
    with BLOQUEO:
        p = ctx.bd.get(Pago, pid)
        if not p or p.estado != "devuelto":
            raise HTTPException(409, "Solo se reintentan pagos devueltos.")
        f = ctx.bd.get(Factura, p.factura_id)
        from kauta import motor
        reglas = agente.reglas_vigentes(ctx.bd)
        d = motor.evaluar({"factura_id": f.id, "extraccion": f.extraccion, "hashes": f.hashes}, reglas,
                          agente.beneficiarios_motor(ctx.bd), agente.historial(ctx.bd, excluir=f.id))
        if d.fallas("frenar") or (d.decision != "pagar" and not any(a.accion == "aprobar" for a in f.aprobaciones)):
            raise HTTPException(409, "Antes de reintentar, Kauta volvió a evaluar la factura y ya no cumple: " + d.motivo)
        intento = len(ctx.bd.execute(select(Pago).where(Pago.factura_id == f.id)).scalars().all()) + 1
        try:
            nuevo = pagos.crear_y_ejecutar(ctx.bd, f, agente.reglas_vigentes(ctx.bd), ctx.actor, riel=datos.riel, intento=intento)
        except ValueError as e:
            raise HTTPException(409, str(e))
        f.estado = "pagada"
        f.motivo = f"Pagada en el intento {intento} por {nuevo.riel} tras la devolución de {pid}. " + f.motivo_inicial
        ctx.bd.commit()
    return pagos.a_dict(nuevo)


@r.get("/rieles")
def rieles(ctx: Contexto = Depends(requiere("ver"))):
    return [{"codigo": k, **v} for k, v in pagos.RIELES.items()]


@r.get("/pagos/{pid}/comprobante")
def comprobante(pid: str, ctx: Contexto = Depends(requiere("ver"))):
    """Comprobante en PDF generado en el servidor (documento simulado, sin validez)."""
    p = ctx.bd.get(Pago, pid)
    if not p:
        raise HTTPException(404)
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    W, H = A5
    c = canvas.Canvas(buf, pagesize=A5)
    c.setTitle(f"Comprobante {p.id}")
    c.setFillColor(HexColor("#0B1B3F"))
    c.rect(0, H - 70, W, 70, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(28, H - 44, "Kauta")
    c.setFont("Helvetica", 9)
    c.drawString(28, H - 60, "Comprobante de pago SIMULADO · Hackathon 30X · sin validez")
    filas = [("Pago", p.id), ("Estado", p.estado.upper()), ("Factura", p.factura_id), ("Beneficiario", p.beneficiario_nombre),
             ("Cuenta", f"···{p.cuenta_ultimos4} · titular confirmado: {p.titular_confirmado or '—'}"),
             ("Riel", pagos.RIELES.get(p.riel, {}).get("nombre", p.riel)), ("Referencia", p.referencia[:44]),
             ("Monto de la factura", f"{p.moneda_factura} {p.monto_factura:,.2f}"),
             ("Recibe el beneficiario", f"{p.moneda_destino} {p.monto_destino:,.2f}"),
             ("Tasa aplicada", f"{p.tasa_aplicada:,.4f} {p.moneda_destino}/USD" if p.moneda_destino != "USD" else "No aplica"),
             ("Costo base", f"USD {p.monto_usd:,.2f}"), ("Comisión del riel", f"USD {p.comision_usd:,.2f}"),
             ("Costo cambiario", f"USD {p.costo_fx_usd:,.2f}"),
             ("Costo total", f"USD {p.monto_usd + p.comision_usd + p.costo_fx_usd:,.2f}"),
             ("Firma de la orden", p.firma[:32]), ("Idempotencia", p.clave_idempotencia[:44]),
             ("Creado", p.creado_en.strftime("%Y-%m-%d %H:%M:%S UTC"))]
    y = H - 100
    for k, v in filas:
        c.setFillColor(HexColor("#5B6782"))
        c.setFont("Helvetica", 8.5)
        c.drawString(28, y, k)
        c.setFillColor(HexColor("#1A1F2B"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(150, y, str(v))
        y -= 17
    if p.motivo_devolucion:
        c.setFillColor(HexColor("#C2410C"))
        c.drawString(28, y - 6, f"Devuelto: {p.motivo_devolucion}"[:90])
    c.setFillColor(HexColor("#5B6782"))
    c.setFont("Helvetica", 7)
    c.drawString(28, 24, "Ningún dinero real se movió. Documento generado por el simulador de pagos de Kauta.")
    c.save()
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="comprobante-{p.id}.pdf"'})
