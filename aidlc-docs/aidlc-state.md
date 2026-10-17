# Estado de AI-DLC: Kauta, el agente que paga por la empresa

Entrega: domingo 2026-10-18 12:00 (se congela a las 10:00). Actualizado: 2026-10-17, sobre el commit `7a9e108`. Fuentes: `inception/hechos-del-codigo.md`, `docs/PRD.md`, `docs/designs/kauta-estado-2026-10-17.md`. Las pruebas no se ejecutaron para este estado. Todos los datos son ficticios.

## Etapas
| Etapa | Estado |
|---|---|
| Requisitos | `inception/requirements/requirements.md` (RF/RNF con evidencia) |
| Personas | `inception/personas.md` |
| Diseño de aplicación y unidades | `inception/application-design/components.md` y `unit-of-work.md` |
| Arquitectura objetivo frente a lo construido | `inception/architecture-target-vs-mvp.md` |
| Plan de ejecución | `inception/plans/execution-plan.md` |
| Guion de 3 minutos | `inception/demo-script.md` |
| Ficha de hechos del código | `inception/hechos-del-codigo.md` (17 secciones) |
| Construcción | Código ya existente en `kauta/`; no hay planes de código por unidad (NO DOCUMENTADO) |

## Estado por componente
| Componente | Hecho (evidencia) | Pendiente |
|---|---|---|
| Núcleo `kauta/` | 13 reglas, extractores XML/texto/OCR, normalización (hechos §3, §6) | Lectura real con IA de un documento nuevo; el set se lee de referencia |
| Servidor `servidor/` | API, roles, doble firma, pagos, wallet, auditoría, costos (hechos §4, §7, §8) | Un solo proceso; sin migraciones; tabla `idempotencia` sin uso (hechos §5, §17) |
| Pantalla `web/` | 11 rutas, selector de persona, recibo y Rendimiento (hechos §12) | Sin login ni activación de TOTP en pantalla (hechos §9) |
| Datos `data/` | 20 facturas con esperado 9/5/6; 4 sorpresa (hechos §15) | Más casos para evaluación independiente (pregunta abierta) |
| Pruebas | 60 funciones, 76 casos por conteo (hechos §13) | Ejecución verificada; CI en GitHub Actions (`TODOS.md`) |
| Seguridad | Sesión, CSRF, cifrado, firmas, detector de instrucciones (hechos §9) | Verificador independiente y ataque con variantes; rotación de claves |
| Despliegue | API con HTTPS en `kauta.2-25-233-186.sslip.io`, systemd y nginx (hechos §14) | Vercel: falta la URL para autorizar el origen |
| Notificaciones | No existen | Aviso por Telegram o correo por segunda firma pendiente |
| Documentación | Ficha de hechos y documentos de inception de esta etapa | `docs/c4/*` (las genera otro agente); documentos de construcción |

## Decisión pendiente
Qué entra antes del congelamiento de las 10:00 del domingo, en el orden del PRD §14: lectura real con costo, evidencia de seguridad independiente, URL de Vercel, aviso de Telegram y video. Pregunta abierta: si se permite tocar el repositorio para el verificador y quién lo revisa (`PRD.md` §15).

## Pendientes de personas
| Pendiente | Para qué |
|---|---|
| Clave `ANTHROPIC_API_KEY` | Lectura real de una factura nueva con costo medido |
| URL de Vercel | Autorizar el origen exacto en `KAUTA_ORIGENES_ADICIONALES` y reiniciar la API |
| Bot de Telegram (@BotFather) | Aviso de segunda firma |
| Confirmar el modo (`demo` o `produccion`) del servidor desplegado | Con `produccion` el selector de persona responde 404 (NO VERIFICADO) |
| Video de 3 minutos y ensayo desde ventana limpia | Entrega |
