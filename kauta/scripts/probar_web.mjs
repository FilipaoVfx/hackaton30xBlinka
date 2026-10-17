/** Recorrido real de la demo, errores de red, 401 y controles a dos tamaños. */
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(new URL('../web/package.json', import.meta.url));
const { chromium } = require('playwright');
const base = process.env.KAUTA_URL || 'http://127.0.0.1:8840';
const salida = resolve(process.argv[2] || 'capturas_web');
await mkdir(salida, { recursive: true });
const navegador = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}), args: ['--no-sandbox'] });
const resultados = [];
async function esperar(p, selector) { await p.locator(selector).first().waitFor({ state: 'visible', timeout: 25000 }); }
async function cambiar(p, nombre) {
  await p.getByRole('button', { name: 'Elegir persona', exact: true }).click();
  const boton = p.getByRole('dialog').getByRole('button').filter({ hasText: nombre });
  await boton.click();
  await p.getByRole('dialog').waitFor({ state: 'hidden' });
}
async function abrir(p, ruta) {
  await p.goto(`${base}/#/${ruta}`);
  await esperar(p, 'main h1');
  await p.locator('[aria-label="Cargando"]').waitFor({ state: 'hidden' }).catch(() => {});
}
async function sinRecorte(p, etiqueta) {
  const medidas = await p.evaluate(() => ({ ancho: innerWidth, contenido: document.documentElement.scrollWidth }));
  assert.ok(medidas.contenido <= medidas.ancho + 1, `${etiqueta}: recorte horizontal ${JSON.stringify(medidas)}`);
}
try {
  for (const [nombre, width, height] of [['escritorio', 1440, 1000], ['movil', 390, 844]]) {
    const ctx = await navegador.newContext({ viewport: { width, height }, locale: 'es-CO', timezoneId: 'America/Bogota' });
    const p = await ctx.newPage();
    const errores = [];
    p.on('pageerror', e => errores.push(e.message));
    await abrir(p, 'resumen');
    await esperar(p, '[data-testid="metricas"]');
    assert.equal(await p.locator('[data-metrica]').count(), 4);
    await cambiar(p, 'Tomás Herrera');
    await abrir(p, 'simulador');
    await p.getByRole('button', { name: 'Restablecer la demo', exact: true }).click();
    await p.getByRole('button', { name: 'Con las 20 facturas del set', exact: true }).click();
    await p.getByRole('dialog').waitFor({ state: 'hidden' });
    await cambiar(p, 'Carlos Rivera');
    await abrir(p, 'resumen');
    await esperar(p, '[data-testid="metricas"]');
    await sinRecorte(p, 'resumen');
    if (nombre === 'escritorio') {
      for (const h of [900, 768, 640]) {
        await p.setViewportSize({ width, height: h });
        const menu = await p.locator('.sidebar-nav').evaluate(e => ({ contenido: e.scrollHeight, disponible: e.clientHeight }));
        assert.ok(menu.contenido <= menu.disponible + 1, `Menú con scroll a ${h}px: ${JSON.stringify(menu)}`);
      }
      await p.setViewportSize({ width, height });
    }
    await p.screenshot({ path: `${salida}/resumen-${nombre}.png`, fullPage: true });
    for (const id of ['F01', 'F07']) {
      await abrir(p, `facturas/${id}`);
      await esperar(p, 'text=Lo que costó esta factura');
      await sinRecorte(p, id);
      await p.getByText(id === 'F01' ? 'Pagada' : 'Frenada', { exact: true }).first().waitFor();
      await p.screenshot({ path: `${salida}/${id}-${nombre}.png`, fullPage: true });
    }
    await abrir(p, 'facturas/F12');
    await p.getByLabel('Fecha de vencimiento confirmada').fill('2026-10-30');
    const comentario = p.getByPlaceholder('Ej.: Llamé al número registrado');
    const respuesta = 'Llamé al proveedor: confirmo vencimiento y pago a la cuenta registrada.';
    await comentario.fill(respuesta);
    assert.equal(await comentario.inputValue(), respuesta);
    assert.equal(await p.getByLabel('Fecha de vencimiento confirmada').inputValue(), '2026-10-30');
    await p.getByRole('button', { name: 'Aprobar y pagar', exact: true }).click();
    await p.getByText('Pagada', { exact: true }).first().waitFor();
    await p.getByText('Se pagó a la cuenta registrada', { exact: false }).first().waitFor();
    await sinRecorte(p, 'F12 pagada');
    await p.screenshot({ path: `${salida}/F12-${nombre}.png`, fullPage: true });
    await abrir(p, 'rendimiento');
    await esperar(p, '[data-testid="metricas"]');
    assert.equal(await p.locator('[data-metrica]').count(), 4);
    await p.getByText('Desglosar lectura: XML, texto, OCR e IA', { exact: true }).click();
    await p.getByText('IA simulada', { exact: true }).waitFor();
    await sinRecorte(p, 'rendimiento');
    await p.screenshot({ path: `${salida}/costos-${nombre}.png`, fullPage: true });
    await cambiar(p, 'Mariana Torres');
    await abrir(p, 'resumen');
    await esperar(p, '[data-testid="metricas"]');
    assert.equal(await p.locator('[data-metrica]').count(), 3);
    await p.screenshot({ path: `${salida}/ceo-${nombre}.png`, fullPage: true });
    await abrir(p, 'facturas/F10');
    await p.getByText('1 de 2 firmas', { exact: false }).first().waitFor();
    await p.getByPlaceholder('Ej.: Llamé al número registrado').fill('Segunda firma: contrato y presupuesto confirmados.');
    await p.getByRole('button', { name: 'Aprobar y pagar', exact: true }).click();
    await p.getByText('Pagada', { exact: true }).first().waitFor();
    await sinRecorte(p, 'F10 pagada');
    await p.screenshot({ path: `${salida}/F10-${nombre}.png`, fullPage: true });

    // Un 502 no puede convertirse en un vacío ni en un esqueleto infinito.
    await p.route('**/api/aprobaciones', route => route.fulfill({ status: 502, contentType: 'application/json', body: '{}' }));
    await abrir(p, 'pregunta').catch(() => {});
    await p.getByText('Kauta no responde', { exact: true }).waitFor();
    await p.unroute('**/api/aprobaciones');
    await p.getByRole('button', { name: 'Reintentar', exact: true }).click();
    await p.getByRole('heading', { name: 'Kauta pregunta', exact: true }).waitFor();

    // GET: renueva la sesión una vez y recupera el dato.
    let get401 = 0;
    await p.route('**/api/rendimiento', route => ++get401 === 1 ? route.fulfill({ status: 401, contentType: 'application/json', body: '{}' }) : route.continue());
    await abrir(p, 'rendimiento');
    await esperar(p, '[data-testid="metricas"]');
    assert.equal(get401, 2);
    await p.unroute('**/api/rendimiento');

    // POST: renueva la sesión pero NO repite una acción financiera.
    await abrir(p, 'facturas/F09');
    const comentario401 = p.getByPlaceholder('Ej.: Llamé al número registrado');
    await comentario401.fill('Prueba de sesión vencida: esta acción no debe ejecutarse.');
    let post401 = 0;
    await p.route('**/api/facturas/F09/rechazar', route => { post401++; return route.fulfill({ status: 401, contentType: 'application/json', body: '{}' }); });
    await p.getByRole('button', { name: 'Rechazar', exact: true }).click();
    await p.getByText('Tu sesión se renovó; repite la acción.', { exact: true }).waitFor();
    assert.equal(post401, 1);
    await p.unroute('**/api/facturas/F09/rechazar');

    // Todos los destinos principales cargan sin error y sin recorte horizontal.
    await cambiar(p, 'Tomás Herrera');
    for (const ruta of ['resumen', 'facturas', 'pregunta', 'simulador', 'wallet', 'rendimiento', 'proveedores', 'reglas', 'auditoria', 'seguridad']) {
      await abrir(p, ruta);
      await sinRecorte(p, ruta);
      assert.equal(await p.getByRole('button', { name: 'Reintentar', exact: true }).count(), 0, `${ruta}: error de carga`);
    }
    // Carga real como CTO y comprobación de permisos de la interfaz.
    await abrir(p, 'facturas');
    const carga = p.waitForResponse(r => r.url().endsWith('/api/facturas/cargar') && r.request().method() === 'POST');
    await p.locator('input[type="file"]').setInputFiles(new URL('../data/sorpresa/S03_proveedor-desconocido_FX-001.xml', import.meta.url).pathname);
    const respuestaCarga = await carga;
    assert.equal(respuestaCarga.status(), 200, await respuestaCarga.text());
    await p.waitForURL(/#\/facturas\//);
    await esperar(p, 'main h1');
    assert.equal(await p.getByRole('button', { name: 'Aprobar y pagar', exact: true }).count(), 0);

    // Error de arranque: pantalla global y recuperación explícita.
    await p.route('**/api/auth/yo', route => route.fulfill({ status: 502, contentType: 'application/json', body: '{}' }));
    await p.reload();
    await p.getByText('Kauta no responde', { exact: true }).waitFor();
    await p.unroute('**/api/auth/yo');
    await p.getByRole('button', { name: 'Reintentar', exact: true }).click();
    await esperar(p, 'main h1');
    assert.deepEqual(errores, []);
    // Deja la demo lista para la persona que abra la URL después de las pruebas.
    await abrir(p, 'simulador');
    await p.getByRole('button', { name: 'Restablecer la demo', exact: true }).click();
    await p.getByRole('button', { name: 'Con las 20 facturas del set', exact: true }).click();
    await p.getByRole('dialog').waitFor({ state: 'hidden' });
    resultados.push({ vista: nombre, recorrido: 'ok', paginaErrores: errores, get401, post401, recortes: 0 });
    await ctx.close();
    console.log(`${nombre}: recorrido, 401 GET/POST, 502, carga, permisos y 10 pantallas OK`);
  }
  await writeFile(`${salida}/resultados.json`, JSON.stringify({ base, resultados }, null, 2));
} finally { await navegador.close(); }
