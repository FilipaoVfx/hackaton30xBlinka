"""
Prueba de punta a punta de la pantalla nueva (React + FastAPI) con Playwright, clic a clic:
simulador (pago normal, ataque de cambio de cuenta), doble aprobación con dos personas, un año simulado
y verificación de la auditoría. Guarda capturas para la documentación.
Uso: python scripts/probar_web.py [carpeta_salida]   (servidor en http://127.0.0.1:8000, base recién creada)
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8000"
SALIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("capturas_web")


def entrar(pag, nombre: str) -> None:
    pag.goto(BASE + "/")
    pag.wait_for_load_state("networkidle")
    pag.get_by_role("button", name=nombre).first.click()
    pag.wait_for_selector("main")
    pag.wait_for_load_state("networkidle")


def cambiar_a(pag, nombre: str, movil: bool) -> None:
    if movil:
        pag.locator("header button").last.click()
    else:
        pag.get_by_role("button", name="Cambiar de persona").click()
    pag.get_by_role("dialog").get_by_role("button", name=nombre).click()
    pag.wait_for_timeout(800)


def escenario(pag, titulo: str) -> None:
    pag.goto(f"{BASE}/#/simulador")
    pag.wait_for_load_state("networkidle")
    pag.get_by_role("button", name="Noviembre de 2026").click() if pag.get_by_role("button", name="Noviembre de 2026").count() else None
    pag.get_by_role("button", name=titulo).first.click()
    pag.wait_for_load_state("networkidle")
    pag.wait_for_timeout(300)
    antes = pag.locator("#resultado h2").first.inner_text() if pag.locator("#resultado h2").count() else ""
    pag.get_by_role("button", name="Enviar a Kauta").click()
    pag.wait_for_function("(a) => { const h = document.querySelector('#resultado h2'); return h && h.innerText !== a && !h.innerText.startsWith('3.'); }",
                          arg=antes, timeout=10000)
    pag.wait_for_load_state("networkidle")


def sin_barra_movil(pag, ocultar: bool) -> None:
    """La barra inferior del celular es fija: se oculta mientras se captura un elemento más alto que la pantalla
    (si no, aparece encima del contenido). Se usa el CSSOM, que la CSP estricta sí permite."""
    pag.evaluate("(o) => document.querySelectorAll('nav[aria-label=Secciones]').forEach(n => n.style.visibility = o ? 'hidden' : '')",
                 ocultar)


def capturar_resultado(pag, ruta: Path, movil: bool) -> None:
    if movil:
        sin_barra_movil(pag, True)
    pag.locator("#resultado").screenshot(path=str(ruta))
    if movil:
        sin_barra_movil(pag, False)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    errores: list[str] = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nombre_vista, (w, h, esc) in {"escritorio": (1440, 900, 1.5), "movil": (390, 844, 2)}.items():
            movil = nombre_vista == "movil"
            ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=esc, locale="es-CO", timezone_id="America/Bogota")
            pag = ctx.new_page()
            pag.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
            pag.on("console", lambda m: errores.append(m.text) if m.type == "error" and "401" not in m.text else None)
            entrar(pag, "Jurado Hackathon 30X")
            pag.goto(f"{BASE}/#/simulador")
            pag.get_by_role("button", name="Restablecer la demo").click()
            pag.get_by_role("button", name="Con las 20 facturas del set").click()
            expect(pag.get_by_text("Demo restablecida").first).to_be_visible(timeout=40000)

            # 1. Factura en regla: se paga sola y el dinero viaja por el riel
            escenario(pag, "Factura en regla")
            expect(pag.locator(".sello").first).to_have_text("Pagar", timeout=8000)
            pag.wait_for_timeout(7000)  # deja terminar la animación del pago
            capturar_resultado(pag, SALIDA / f"sim_pago_{nombre_vista}.png", movil)
            if not movil:
                pag.screenshot(path=str(SALIDA / "sim_pago_pantalla.png"))

            # 2. Ataque: cambio de cuenta bancaria
            escenario(pag, "Cambio de cuenta bancaria")
            expect(pag.locator(".sello").first).to_have_text("Escalar", timeout=8000)
            pag.wait_for_timeout(1500)
            capturar_resultado(pag, SALIDA / f"sim_ataque_{nombre_vista}.png", movil)

            # 3. Instrucción oculta para la IA
            escenario(pag, "Instrucción oculta para la IA")
            expect(pag.locator(".sello").first).to_have_text("Escalar", timeout=8000)

            # 4. Doble aprobación: monto alto → firma del jurado y luego de Mariana
            escenario(pag, "Monto alto: doble aprobación")
            expect(pag.locator(".sello").first).to_have_text("Escalar", timeout=8000)
            pag.wait_for_timeout(1500)
            pag.get_by_role("link", name="Responder a Kauta").click()
            pag.wait_for_load_state("networkidle")
            pag.get_by_placeholder("Ej.: Llamé al número registrado").fill("Proyecto especial aprobado por el comité de gerencia.")
            pag.get_by_role("button", name="Firmar aprobación 1 de 2").click()
            pag.wait_for_timeout(1200)
            cambiar_a(pag, "Mariana Torres", movil)
            pag.wait_for_load_state("networkidle")
            pag.get_by_placeholder("Ej.: Llamé al número registrado").fill("Confirmo el proyecto especial como segunda firmante.")
            pag.get_by_role("button", name="Aprobar y pagar").click()
            expect(pag.get_by_text("Pagada con aprobación de").first).to_be_visible(timeout=8000)
            pag.wait_for_timeout(4800)  # deja que se cierren los avisos para que no tapen la captura
            pag.screenshot(path=str(SALIDA / f"doble_aprobacion_{nombre_vista}.png"), full_page=True)

            # 5. Un año simulado: 0 pagos indebidos
            pag.goto(f"{BASE}/#/simulador")
            pag.get_by_role("tab", name="Simular un año").click()
            pag.get_by_role("button", name="Correr la simulación").click()
            expect(pag.get_by_text("Pagos indebidos")).to_be_visible(timeout=15000)
            pag.wait_for_timeout(500)
            pag.screenshot(path=str(SALIDA / f"sim_anio_{nombre_vista}.png"), full_page=True)

            # 6. Auditoría íntegra
            pag.goto(f"{BASE}/#/auditoria")
            expect(pag.get_by_text("Cadena íntegra").first).to_be_visible(timeout=8000)
            pag.goto(f"{BASE}/#/resumen")
            pag.wait_for_load_state("networkidle")
            pag.wait_for_timeout(600)
            pag.screenshot(path=str(SALIDA / f"resumen_final_{nombre_vista}.png"), full_page=True)
            ctx.close()
        nav.close()
    print("Flujo completo superado. Capturas en", SALIDA)
    for e in sorted(set(errores)):
        print("  ", e)


if __name__ == "__main__":
    main()
