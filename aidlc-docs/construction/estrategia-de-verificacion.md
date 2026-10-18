# Estrategia de verificación

Qué pruebas tiene Kauta hoy, qué mide cada una, cómo se ejecutan y qué no está probado. Fuente: `aidlc-docs/inception/hechos-del-codigo.md` §13, `kauta/README.md` (sección Verificación) y `docs/designs/kauta-estado-2026-10-17.md`. Los conteos salen de leer `def test_` y los `parametrize`; en esta documentación no se ejecutó nada.

## Resumen

| Capa | Herramienta | Cantidad |
|---|---|---|
| Motor, formatos, servidor y costos | pytest | 60 funciones, 76 casos (2 `parametrize` de 13 y 5 casos) |
| Recorrido web | Playwright (`scripts/probar_web.mjs`) | 1 recorrido; no entra en la cuenta de 76 |
| Tipos y compilación del front | `tsc --noEmit` y `vite build` | 2 comprobaciones |
| Mediciones | scripts en `kauta/scripts/` | 4 scripts; no son pruebas automáticas |

## Pruebas por archivo (`kauta/tests/`)

| Archivo | Funciones | Casos | Qué cubre |
|---|---|---|---|
| `test_kauta.py` | 9 | 9 | Las 20 facturas del set coinciden con `data/esperado.csv`; las 13 reglas explican; una instrucción dentro del documento no cambia la decisión; aprobar no rompe reglas duras; cambiar reglas reevalúa; el registro encadenado detecta alteración; montos LatAm y EE. UU.; un error inesperado escala; estrés con 0 pagos fuera de reglas. Usa el agente en memoria `kauta/agente.py` |
| `test_formatos.py` | 17 | 33 | Identificaciones fiscales (13 casos), CNPJ alfanumérico, validadores bancarios, montos (5), fechas por país, monedas, CFDI exacto, contenedor DIAN en ZIP, XXE, zip slip y bomba, totales que no cuadran, QR de ARCA, XML luego PDF duplicado, archivo malicioso, notas crédito nunca se pagan |
| `test_servidor.py` | 28 | 28 | Set 20 de 20 por la API; sesión y CSRF; permisos por rol; regla dura no se salta aprobando; doble aprobación y firmas; firma alterada bloquea; un solo pago vivo por factura; auditoría y libro cuadrado; simulador de año; carga rechaza tipos falsos; persona sin contraseña; cambio de reglas no paga solo; costos idempotentes; restablecer determinista; recorrido F12; orígenes públicos; falla tras crear un pago revierte todo |
| `test_costos.py` | 6 | 6 | Costo por resuelta y de pagar; invariante recibos = numerador; cobertura; costo desconocido no es cero; mes cerrado no cambia los recibos |
| `conftest.py` | 0 | 0 | Fija `KAUTA_VAR` y `KAUTA_BD` temporales antes de importar el servidor y limpia al final |

Total: 9 + 33 + 28 + 6 = 76. Coincide con "pasan 76 pruebas" del estado (`docs/designs/kauta-estado-2026-10-17.md:9`); la cifra de ejecución viene de ese documento, no de una corrida hecha aquí.

Invariantes que protegen las pruebas: la IA no decide pagos (la decisión sale del motor determinista), reglas duras no se saltan con firmas, nunca hay pagos fuera de reglas en el set ni bajo estrés, y un pago fallido no deja rastro de costos ni asientos.

## Scripts de medición (no son pruebas)

| Script | Qué mide | Evidencia |
|---|---|---|
| `scripts/correr_set.py` | Corre el set en modo demo o IA (`--modo ia`) y muestra decisiones | `correr_set.py:1-8` |
| `scripts/medir_extraccion.py` | Compara la extracción (IA o demo) con `data/referencia_extracciones.json` | `:1-9` |
| `scripts/medir_ocr.py` | Mide el lector local contra las extracciones verificadas | `:1-3` |
| `scripts/contrastar_validadores.py` | Compara los validadores propios con `python-stdnum` y `clabe` sobre 55.000 casos | `:1-2` |

`scripts/generar_set.py` genera `data/*` desde una sola fuente y `scripts/empaquetar.py` arma el zip del kit; no verifican.

## Recorrido web (Playwright)

`scripts/probar_web.mjs` (157 líneas) recorre la app real a 390 y 1440 px: menú a tres alturas, firmas, recibos, F01/F07/F12/F10, dos firmas, permisos, carga de XML, recuperación de lectura ante 401, POST sin repetición y reintento ante 502; restablece la demo al final (`kauta/README.md`, sección Verificación). `scripts/probar_web.py` es un envoltorio. `scripts/capturas_web.py` toma capturas.

## Cómo se ejecuta cada cosa (comandos del README, no ejecutados aquí)

| Qué | Comando (desde `kauta/`) |
|---|---|
| Instalar pruebas | `pip install pytest httpx` (el `requirements.txt` pide `httpx2>=2.0`: NO VERIFICADO que ese paquete exista; discrepancia #3 de hechos §17) |
| Pruebas del servidor | `python -m pytest -q -p no:cacheprovider` |
| Tipos del front | `cd web && npm run typecheck` |
| Compilación | `cd web && npm run build` |
| Navegador para el recorrido | `cd web && npx playwright install chromium` |
| Recorrido web | `KAUTA_URL=http://127.0.0.1:8000 npm run test:e2e -- /tmp/kauta-capturas` (en `web/`), o `python scripts/probar_web.py [salida]` |
| Chromium propio | variable `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` |
| Mediciones | `python scripts/correr_set.py`, `medir_extraccion.py`, `medir_ocr.py`, `contrastar_validadores.py` |

El servidor debe estar arrancado para el recorrido: `uvicorn servidor.main:app --host 127.0.0.1 --port 8000 --workers 1`. El estado indica que las pruebas con TestClient se ejecutaron fuera del sandbox de la sesión.

## Determinismo y aislamiento

| Fuente | Cómo se controla hoy |
|---|---|
| Base de datos | `tests/conftest.py` crea una carpeta temporal antes de recolectar; no se toca `kauta/var/kauta.db` (corregido tras el fallo 71/72 del estado) |
| Extracción del set | Tabla de referencia (`referencia_extracciones.json`), sin red ni IA |
| Red | No hay bloqueo explícito de red: NO ENCONTRADO; las pruebas no necesitan clave de Anthropic |

## Lo que NO está probado

| Hueco | Evidencia |
|---|---|
| Pruebas del front (Vitest, Jest, Testing Library) | NO ENCONTRADO; solo typecheck, build y el recorrido Playwright |
| Atributos `data-testid` | Una sola aparición (`ui.tsx:187`); el recorrido no depende de un conjunto estable |
| Integración continua | NO ENCONTRADO (`TODOS.md:5-15`); todo se corre a mano |
| Concurrencia entre procesos | El presupuesto bajo concurrencia se resuelve con un candado de hilos del proceso; no hay prueba con varios procesos (hechos §17) |
| Lectura real con IA | Las 20 facturas se leen de la tabla de referencia, no por OCR ni IA; la IA y su costo están simulados; `ExtractorIA` no tiene prueba que llame al modelo; la precisión del OCR se mide en un script, no en una prueba |
| Mutación y propiedades | NO ENCONTRADO |
| Despliegue en Vercel y servidor desplegado | NO VERIFICADO |
| Autenticación real | La entrada es el selector sin contraseña; login, TOTP y passkeys no tienen pantalla ni recorrido |
| Cobertura de código | NO ENCONTRADO (no se mide) |
