/** Regresión de carga y respuestas antiguas. Toda la API está simulada: no accede a Gmail. */
import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(new URL('../web/package.json', import.meta.url));
const { chromium } = require('playwright');
const dist = resolve(process.env.KAUTA_TEST_DIST || new URL('../web/dist', import.meta.url).pathname);
const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  const path = resolve(dist, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname === '/' ? '/index.html' : new URL(req.url, 'http://localhost').pathname));
  if (!path.startsWith(dist + sep)) { res.writeHead(404); res.end(); return; }
  try { const body = await readFile(path); res.writeHead(200, { 'Content-Type': mime[extname(path)] || 'application/octet-stream' }); res.end(body); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {}), args: ['--no-sandbox'] });
const base = `http://127.0.0.1:${server.address().port}`;
const doc = { id: 999999, nombre: 'Factura de prueba.xml', estado: 'error_lectura', motivo: 'Prueba de recepción', factura_id: null, asunto: 'Prueba', remitente: 'demo@example.test', recibida_en: '2026-10-01T10:00:00Z' };
try {
  for (const [vista, width, height] of [['escritorio', 1440, 900], ['movil', 390, 844]]) {
    const ctx = await browser.newContext({ viewport: { width, height }, locale: 'es-CO' });
    const p = await ctx.newPage(); p.setDefaultTimeout(5000); p.setDefaultNavigationTimeout(10000); await p.clock.install();
    const errors = []; p.on('pageerror', e => errors.push(e.message));
    let n = 0, deleted = false, releases = {}, resolvePoll;
    const first = new Promise(r => { releases.first = r; });
    const stale = new Promise(r => { releases.stale = r; });
    const pollStarted = new Promise(r => { resolvePoll = r; });
    await p.route('**/api/**', async route => {
      const path = new URL(route.request().url()).pathname, method = route.request().method();
      let data;
      if (path === '/api/auth/yo') data = { usuario: { id: 3, correo: 'demo@example.test', nombre: 'Persona de prueba', cargo: 'CTO', rol: 'cto', rol_nombre: 'CTO', permisos: ['ver', 'facturas.cargar'], csrf: 'prueba-local' } };
      else if (path === '/api/aprobaciones' || path === '/api/facturas') data = [];
      else if (path === '/api/reglas') data = { vigente: { periodo_actual: '2026-10' } };
      else if (path === '/api/correo/estado') data = { estado: 'escuchando', cuenta: 'demo@example.test', asunto: 'kauda', intervalo_segundos: 60, desde: null, ultimo_exito: null, error: null, documentos: { error_lectura: deleted ? 0 : 1 } };
      else if (path === '/api/correo/documentos' && method === 'GET') {
        const request = ++n;
        if (request === 1) await first;
        if (request === 2) { resolvePoll(); await stale; }
        data = request === 2 ? [doc] : deleted ? [] : [doc];
      } else if (path === '/api/correo/documentos/999999' && method === 'DELETE') { deleted = true; data = { ok: true }; }
      else { await route.fulfill({ status: 404, json: { detail: 'API no simulada' } }); return; }
      await route.fulfill({ status: 200, json: data });
    });
    await p.goto(base + '/#/facturas');
    const inbox = p.getByRole('region', { name: 'Recepción automática de correo' });
    await p.getByRole('button', { name: 'Ver recepción', exact: true }).click();
    await inbox.getByText('Cargando recepción…', { exact: true }).waitFor({ timeout: 5000 });
    assert.equal(await inbox.getByText('No hay documentos en recepción.', { exact: true }).count(), 0);
    await p.clock.fastForward(15001);
    assert.equal(n, 1, 'Un poll no debe invalidar una consulta que tarda más de 15 s');
    releases.first(); await inbox.getByText(doc.nombre, { exact: true }).waitFor();
    await p.clock.fastForward(15001); await pollStarted;
    await p.getByRole('button', { name: `Eliminar de recepción: ${doc.nombre}`, exact: true }).click();
    const dialog = p.getByRole('dialog', { name: 'Eliminar de recepción', exact: true });
    await dialog.getByRole('button', { name: 'Cancelar', exact: true }).click();
    assert.equal(deleted, false, 'Cancelar no debe enviar DELETE');
    await p.getByRole('button', { name: `Eliminar de recepción: ${doc.nombre}`, exact: true }).click();
    await dialog.getByRole('button', { name: 'Eliminar de recepción', exact: true }).click();
    await dialog.waitFor({ state: 'hidden' });
    await inbox.getByText('No hay documentos en recepción.', { exact: true }).waitFor();
    const oldResponse = p.waitForResponse(r => new URL(r.url()).pathname === '/api/correo/documentos');
    releases.stale(); await oldResponse; await p.waitForTimeout(100);
    assert.equal(await inbox.getByText(doc.nombre, { exact: true }).count(), 0, 'Una respuesta vieja no debe resucitar un documento retirado');
    assert.deepEqual(errors, []);
    console.log(`${vista}: carga separada del vacío, cancelar, DELETE simulado y respuesta antigua OK`);
    await ctx.close();
  }
} finally { await browser.close(); await new Promise(r => server.close(r)); }
