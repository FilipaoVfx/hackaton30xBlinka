# Registro de tandas

Historial de trabajo de Kauta por commit y por bloque T1 a T13. **Este registro se reconstruyó después de los hechos**: el equipo no lo llevó por tanda; las filas salen de `git log --stat` y de `docs/designs/kauta-estado-2026-10-17.md` (estado). Lo que esas fuentes no dicen figura como NO DOCUMENTADO. Hora de cada commit: zona -0500.

## Commits (fuente: `git log --stat`, hechos §16)

| Fecha y hora | Commit | Qué cambió | Pruebas | Hallazgos |
|---|---|---|---|---|
| 2026-10-16 20:16 | `c5c9713` | `README.md` (+191): alcance del reto y responsabilidades del equipo | n/a | Solo documentación del brief |
| 2026-10-17 09:33 | `ce7ffa8` | `prototipos/` (4 HTML: biblioteca, monitor, planificador, revisor), logos y fuente Inter; `README.md` ampliado (10 archivos, +607 -3) | n/a; los prototipos se comprobaron a mano en Chromium (README raíz) y no validan un backend | Prototipos, no la app |
| 2026-10-17 15:43 | `ffbc43a` | Importa toda la app `kauta/` (145 archivos, +18450): núcleo, servidor, front React, datos, Docker; `docs/designs/kauta-finops-rediseno.md` (1356 líneas); `TODOS.md` | NO DOCUMENTADO cuántas pasaban en este commit; tres archivos de prueba (`test_formatos`, `test_kauta`, `test_servidor`) | Cubre T1 a T5 del plan según el estado (ver bloques) |
| 2026-10-17 15:51 | `b1ee286` | `servicios/costos.py` (133), `servicios/metricas.py` (368), `data/tarifas.json`, tabla `eventos_costo`, `tests/test_costos.py` (100) (11 archivos, +775 -50) | La última ejecución de Claude dejó 71 aprobadas y 1 fallida | Cubre T6 a T8 |
| 2026-10-17 16:22 | `7a9e108` | Quita `Login.tsx` y `Personas.tsx`; reescribe `App.tsx`, `Resumen.tsx`, `Seguridad.tsx`; agrega `Rendimiento.tsx`, `ReciboFactura.tsx`, `ops/*`, `web/vercel.json`, `DESIGN.md`, `scripts/probar_web.mjs`, `tests/conftest.py`; variables `KAUTA_ORIGENES_ADICIONALES` y `KAUTA_PREPARAR_RECORRIDO` (39 archivos, +1117 -1115) | 76 casos (60 funciones) aprobados, más typecheck y build | Cubre T9 a T13; el estado declara que no se confirmó el despliegue en Vercel |

## Bloques T1 a T13 (fuente: `docs/designs/kauta-estado-2026-10-17.md`, tabla "Estado frente al plan")

El estado se escribió al revisar `b1ee286`; la columna "Estado al 2026-10-17 cierre" resume el texto de "Continuación terminada" (mismo documento).

| Bloque | Tema | Estado observado en la revisión de `b1ee286` | Estado al cierre (`7a9e108`) |
|---|---|---|---|
| T1 | Importación | Código en git; sin repetir auditoría de secretos ni clon limpio | NO VERIFICADO que se repitiera |
| T2 | Roles y semilla | Tres roles; falta el cierre del guion con F10 | F10 con preparación opcional: presupuesto simulado USD 20.000 y primera firma CFO (`KAUTA_PREPARAR_RECORRIDO`) |
| T3 | Persona y reentrada | Endpoint probado; falta recuperación 401 en el cliente | Hecho: recuperación 401 |
| T4 | Vencimiento en R01 | Implementado; suite del set aprobada | Sin cambio; F12 exige confirmar vencimiento antes de aprobar |
| T5 | Reevaluación | Implementado y con pruebas | Sin cambio |
| T6 a T8 | Costos, métricas, semilla | Implementados; pruebas de aceptación, conciliación, IA x10 y restablecimiento aprobadas | Sin cambio |
| T9 | Front sin login y errores | Pendiente | Hecho: selector sin contraseña, errores con reintento |
| T10 | Rediseño y vistas | Pendiente | Hecho: resumen por rol, recibo, Rendimiento, `DESIGN.md` |
| T11 | Orígenes | Existe `KAUTA_ORIGEN`; falta el origen público definitivo | Parcial: falta la URL de Vercel para autorizar ese origen |
| T12 | Despliegue | Pendiente | `ops/kauta.service`, `ops/nginx.kauta`, `web/vercel.json` creados; API habilitada con HTTPS en el host `kauta.2-25-233-186.sslip.io`; Vercel no se declara desplegado |
| T13 | Recorrido web | Pendiente | `scripts/probar_web.mjs` (Playwright) cubre F01, F07, F12, F10, dos firmas, permisos, carga XML y recuperación 401/502 |

## Pruebas por hito

| Momento | Resultado | Fuente |
|---|---|---|
| Fin de `b1ee286` | 71 aprobadas, 1 fallida (`test_personas_invitacion_registro_y_roles`, 409 por usuario ya existente) | estado, "Punto de continuación" |
| Corrección local | 73 aprobadas; configuración temporal movida a `tests/conftest.py` | estado |
| Cierre (`7a9e108`) | 76 aprobadas, incluida una falla forzada tras crear un pago | estado; conteo por lectura: hechos §13 |

## Hallazgos del estado que condicionaron el trabajo

| # | Hallazgo | Resolución |
|---|---|---|
| 1 | F10 no estaba preparada para el cierre de la demo; `test_regla_dura_no_se_salta_aprobando` exige 409 por R12 | Preparación opcional y auditada; el set oficial no se modifica |
| 2 | El plan mezclaba decisiones antiguas y nuevas sobre invitaciones | La API se conserva (D8); se quitó la pantalla Personas |
| 3 | El despliegue cambió durante la revisión | Decisión D6: API y SQLite en el servidor propio, front en Vercel con proxy |
| 4 | Suite verde no valida la interfaz pendiente | Recorrido Playwright a 390 y 1440 px |

Pendiente a esta fecha: URL de Vercel y autorizarla en `KAUTA_ORIGENES_ADICIONALES`; integración continua (`TODOS.md`).
