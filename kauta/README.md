# Kauta · el agente que paga por la empresa

Kauta lee documentos, los revisa contra 13 reglas y paga, frena o pregunta.
La IA lee; el código decide. Demo del Reto Blinka · Hackathon 30X.
Todos los proveedores, documentos, costos y pagos son ficticios.

La aplicación React y FastAPI tiene tres vistas: CFO, CEO y CTO. Abre como
CFO y permite cambiar de persona sin contraseña. Esa elección demuestra
permisos y doble control; no autentica la identidad de quien abre la URL.

| Persona | Rol | Acciones principales |
| --- | --- | --- |
| Carlos Rivera | CFO | Firmar, editar políticas, fondear y verificar cuentas |
| Mariana Torres | CEO | Revisar resultados y poner la segunda firma |
| Tomás Herrera | CTO | Cargar documentos, operar el agente y restablecer la demo |

## Arranque local

Python 3.12, Node 22 y Tesseract con español/inglés para OCR.
El repositorio no incluye `web/dist`: hay que compilar la pantalla.

```bash
cd kauta
python -m venv .venv
# Activar .venv según el sistema operativo
pip install -r requirements-servidor.txt
cd web
npm ci
npm run typecheck
npm run build
cd ..
uvicorn servidor.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Abra http://localhost:8000. El primer arranque genera claves de demo y la base
en `var/`, ignorado por git. Defina `KAUTA_VAR` para guardar esos datos fuera
del checkout. No defina `ANTHROPIC_API_KEY` durante la demo: la extracción del
set y sus costos de IA son simulados y no requieren llamadas pagadas.

El set oficial empieza con 9 pagadas, 5 frenadas y 6 pendientes. Para ensayar
el guion, active `KAUTA_PREPARAR_RECORRIDO=1` antes de iniciar, o entre como
CTO → Simulador → Restablecer la demo → Con las 20 facturas del set.
La preparación amplía el presupuesto simulado a USD 20.000, registra la
primera firma de F10 por Carlos y mantiene la segunda pendiente del CEO.
Ambas operaciones quedan auditadas. Los documentos y el motor no se alteran.
El API `POST /api/demo/restablecer` sin `preparar_recorrido` recupera el set
oficial. Ningún restablecimiento se ejecuta automáticamente al recargar la página.

## Recorrido de demostración

1. CFO → Resumen: cuatro métricas del dinero y facturas que necesitan su firma.
2. F01: pago automático, motivo, 13 reglas y recibo de costos.
3. F07: duplicado frenado, sin pago y con dinero protegido.
4. F12: confirmar vencimiento y cuenta por un canal independiente; comentar y
   aprobar. Kauta paga a la cuenta registrada ···8152, nunca a la que pide el documento.
5. Rendimiento y costos: cuatro métricas comunes a todos los roles; desglose de
   lectura XML/texto/OCR/IA. Los importes provienen del mismo libro que los recibos.
6. Cambiar a CEO → F10: segunda firma y pago, con las reglas duras verificadas otra vez.

Cada pantalla declara los costos simulados y los tiempos humanos estimados.
“—” significa desconocido; el cero conocido sí es cero. La infraestructura se
reparte provisionalmente entre facturas finales hasta que termina el mes en Bogotá.

## Importación manual en Vercel

El despliegue aprobado separa la pantalla y la API: Vercel sirve React y
reenvía `/api/*` por HTTPS al servidor, donde permanecen SQLite y el OCR.

Al importar `FilipaoVfx/hackaton30xBlinka` desde GitHub:

| Opción | Valor |
| --- | --- |
| Rama | `main` con los cambios de este trabajo publicados |
| Root Directory | `kauta/web` |
| Framework | Vite |
| Node.js | 22.x |
| Install Command | `npm ci` |
| Build Command | `npm run typecheck && npm run build` |
| Output Directory | `dist` |

`web/vercel.json` contiene el proxy a
`https://kauta.2-25-233-186.sslip.io/api/:path*`, el fallback SPA y las
cabeceras. No ponga claves de IA, de firma ni la base de datos en variables
`VITE_*`: esas variables son públicas. La pantalla no necesita variables de entorno.

**Después de que Vercel asigne la URL**, autorice ese origen exacto en el
servidor mediante `KAUTA_ORIGENES_ADICIONALES=https://su-proyecto.vercel.app`
y reinicie la API. El import puede compilar antes de eso, pero la entrada por
persona y las firmas responderán 403 hasta que el origen esté autorizado.
Cada dominio de preview es independiente: no se acepta un comodín `*.vercel.app`.

La API debe usar un solo proceso: el candado de negocio es local al proceso.
Los archivos de instalación están en `ops/kauta.service` y `ops/nginx.kauta`.
Se requiere certificado válido del host de la API. `KAUTA_ORIGEN` debe ser un
origen HTTPS para emitir la cookie Secure. La cookie es HttpOnly, sin Domain;
Vercel la entrega en el mismo origen de la pantalla a través del rewrite.
Los datos y claves de runtime deben permanecer fuera del repositorio.

## Verificación

```bash
pip install pytest httpx
python -m pytest -q -p no:cacheprovider
cd web
npm run typecheck
npm run build
npx playwright install chromium
KAUTA_URL=http://127.0.0.1:8000 npm run test:e2e -- /tmp/kauta-capturas
```

También puede ejecutar `python scripts/probar_web.py [salida]` desde `kauta/`.
`KAUTA_URL` selecciona el servidor; `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`
permite utilizar un Chromium ya instalado. El recorrido prueba 390/1440 px,
menú a tres alturas, firmas, recibos, carga XML, permisos, recuperación GET
ante 401, POST sin repetición y reintento de 502. Restablece la demo al final.

La suite configura una base temporal desde `tests/conftest.py`, antes de
importar la aplicación, para no reutilizar ni modificar la base local.

## Estructura

- `kauta/`: motor determinista, extractores XML/texto/OCR y normalización fiscal.
- `servidor/`: FastAPI, sesiones/CSRF, roles, pagos, wallet, auditoría y libro de costos.
- `web/`: React, TypeScript, Vite, Tailwind e Inter local; tokens en `DESIGN.md`.
- `data/`: empresa, reglas, tarifas simuladas, documentos y resultados del set.
- `tests/`: núcleo, formatos, controles de servidor y conciliación de costos.
- `scripts/`: mediciones y recorrido web reproducible.

La API heredada de contraseñas, invitaciones y TOTP conserva sus pruebas de
regresión según la decisión D8. No forma parte de la interfaz pública de esta demo.
El plan B Streamlit sigue disponible con las dependencias de `requirements.txt`.

Diseño y planning: [sistema de interfaz](DESIGN.md), [plan aprobado](../docs/designs/kauta-finops-rediseno.md) y [estado de ejecución](../docs/designs/kauta-estado-2026-10-17.md).
