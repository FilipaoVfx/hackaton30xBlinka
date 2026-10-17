# PRD de Kauta: el agente que paga por la empresa

Reto Blinka · Hackathon 30X. Entrega: domingo 2026-10-18, 12:00 (se congela a las 10:00).
Versión: 2026-10-17, escrita a partir del código y los documentos del repositorio (`kauta/README.md`, `kauta/DESIGN.md`, `docs/designs/*`, `kauta/data/*`). Lo que no se pudo comprobar en el código va marcado **NO VERIFICADO**. Todos los proveedores, documentos, costos y pagos son ficticios.

## 1. Resumen
Kauta lee facturas (PDF, XML, correo, chat, foto), las revisa contra 13 reglas de código y decide **pagar, frenar o preguntar** a una persona. La IA lee; el código decide. Tiene tres personas (CFO, CEO y CTO) con doble firma, y cada pago trae un recibo con su costo (libro de costos FinOps). No mueve dinero real.

## 2. Problema
Una empresa con proveedores en varios países recibe cuentas por correo, PDF, foto o chat. Finanzas las revisa a mano, las compara con lo acordado, pide aprobaciones y paga. Es lento, depende de personas y un error cuesta dinero. El reto pide un agente que automatice lo repetitivo y deje a una persona lo dudoso, con la regla de oro: **ningún pago indebido** (descalifica) y toda decisión explicable.

## 3. Objetivos y criterios de éxito
| Criterio del reto | Cómo lo mide Kauta |
|---|---|
| Autonomía | Set oficial de 20 facturas: 9 pagadas, 5 frenadas, 6 pendientes de una persona (README). Reportar con el resultado esperado de `kauta/data/esperado.csv` |
| Seguridad | Ninguna factura con regla dura pasa a pago; F10 se bloquea por R12 aunque se intente aprobar; el pago va a la cuenta registrada, nunca a la del documento (F12) |
| Explicabilidad | Cada decisión con su motivo, la tira de 13 reglas y el recibo con costos |
| Diferenciación | Recibo con economía de cada pago (libro FinOps) y tres personas con doble control |

Métricas de cabecera (máximo 4 por pantalla): dinero pagado, dinero protegido, costo por factura resuelta, facturas pendientes de firma. Cada métrica declara numerador, denominador y cobertura; "—" es desconocido, no cero.

## 4. Personas
| Persona | Rol | Puede (README) | No puede (deducido de "quien carga no aprueba"; NO VERIFICADO en el código) |
|---|---|---|---|
| Carlos Rivera | CFO | Firmar, editar políticas, fondear, verificar cuentas | Poner la segunda firma de una factura que ya firmó él |
| Mariana Torres | CEO | Revisar resultados y poner la segunda firma | Cargar documentos |
| Tomás Herrera | CTO | Cargar documentos, operar el agente, restablecer la demo | Aprobar pagos |

Quien carga no aprueba. La elección de persona es sin contraseña: demuestra permisos y doble control, no autentica a quien abre la URL (la pantalla lo dice).

## 5. Alcance
**Incluye:** lectura de XML (UBL/CFDI), texto, OCR local (Tesseract es/en) y lectura simulada de IA; 13 reglas; 0, 1 o 2 firmas según las reglas; wallet simulada; libro de costos y vista "Rendimiento y costos"; auditoría; simulador; recorrido de demo; API desplegada y front en Vercel.
**No incluye:** mover dinero real, login real, pagos por rieles reales, llamadas a modelos pagados durante la demo (la clave `ANTHROPIC_API_KEY` queda sin definir), servidor MCP.

## 6. Reglas del motor (13)
Definidas en `kauta/kauta/motor.py` y los umbrales en `kauta/data/reglas.json` (USD 3.000 de aprobación humana, USD 10.000 máximo por pago, USD 4.000 por beneficiario y periodo, USD 15.000 de presupuesto del periodo; monedas USD, COP y MXN).
Efectos confirmados en el código y en el set: R01 lectura con baja confianza (escala), R02 moneda no permitida (escala), R03 duplicado exacto (frena), R04 duplicado disfrazado (frena), R05 beneficiario bloqueado (frena), R06 beneficiario nuevo (escala), R07 cuenta distinta de la registrada (escala), R08 no cuadra con lo acordado (escala), R09 límite máximo por pago (frena), R10 umbral de aprobación humana (escala), R11 límite por beneficiario en el periodo (escala), R12 saldo insuficiente (frena), R13 instrucción sospechosa en el documento (escala). Prioridad de escalada: R06, R13, R07, R01, R08, R10, R11, R02.

## 7. Flujo
1. El CTO carga el documento. El extractor lo lee por XML, texto, OCR o IA simulada y lo normaliza (fiscal, monedas).
2. El motor evalúa las 13 reglas y decide pagar, frenar o preguntar.
3. Si pregunta, la factura espera la firma del CFO y, cuando corresponde, del CEO. Antes de pagar se verifican de nuevo las reglas duras.
4. El pago sale de la wallet simulada hacia la **cuenta registrada** del proveedor y deja su recibo, con costos (lectura, revisión humana, comisión, cambio, infraestructura).
5. Todo queda en la auditoría.

## 8. Set de prueba y casos clave
20 facturas ficticias en `kauta/data/facturas/` (PDF, correo, chat, imagen). Resultados esperados en `kauta/data/esperado.csv`. Casos de demostración:
- **F01** pago automático con recibo.
- **F07** duplicado frenado (dinero protegido).
- **F12** cuenta distinta (0093 frente a la registrada ···8152): confirmar por un canal independiente; paga a la registrada.
- **F10** supera el umbral: primera firma del CFO y segunda del CEO; sigue bloqueada por R12 si el saldo no alcanza (por eso el recorrido usa la preparación opcional de presupuesto USD 20.000).
- **F08** trae una instrucción oculta para el agente.

## 9. Arquitectura
| Capa | Contenido |
|---|---|
| `kauta/` | Motor determinista, extractores XML/texto/OCR, normalización fiscal, agente |
| `servidor/` | FastAPI, sesiones y CSRF, roles, pagos, wallet, auditoría, libro de costos |
| `web/` | React, TypeScript, Vite y Tailwind; tokens en `kauta/DESIGN.md` |
| `data/` | Empresa, reglas, tarifas simuladas, documentos y resultados del set |
| Despliegue | Vercel sirve la pantalla (`kauta/web`) y reenvía `/api/*` por HTTPS al servidor, que mantiene SQLite y OCR en un solo proceso (`ops/kauta.service`, `ops/nginx.kauta`) |
Seguridad ya construida: firma (`servidor/seguridad/firma.py`), detección de instrucciones en el documento (`kauta/extractor.py`), cookie HttpOnly y Secure, origen autorizado exacto. Costos de IA y extracción del set **simulados** y determinista.

## 10. Calidad y verificación
- Pruebas: 76 aprobadas según el estado del 2026-10-17 (`docs/designs/kauta-estado-2026-10-17.md`; el mismo documento menciona 73 antes de la continuación); TypeScript y build aprobados. No se volvió a ejecutar para este documento (**NO VERIFICADO**).
- Recorrido Playwright de 390 a 1440 px: selector de persona, F01/F07/F12/F10, dos firmas, permisos, carga XML y recuperación 401/502.
- Sin verificador independiente ni evaluación adversarial publicada (brecha, ver sección 12).

## 11. Estado al 2026-10-17
| Bloque | Estado |
|---|---|
| Motor, set de 20, roles, costos y métricas | Hecho |
| Selector de persona y recuperación 401, recibo con costos, Rendimiento | Hecho según el README; parte figuraba pendiente en el estado de la mañana |
| API en `kauta.service` con HTTPS | Hecho |
| Front en Vercel | Pendiente: falta la URL para autorizar el origen en la API |
| Aviso por Telegram o correo | No existe en el código (**NO VERIFICADO** fuera de `web/src/ui.tsx`) |
| Lectura con modelo en vivo | No: simulada a propósito para la demo |

## 12. Riesgos y brechas propias
| Brecha | Riesgo | Respuesta propuesta |
|---|---|---|
| La extracción es simulada | El jurado no ve leer una factura nueva | Lectura real con clave para un documento nuevo, con su costo medido en el libro |
| Sin evidencia independiente de seguridad | Un set de 20 convence poco | Verificador independiente, ataque con variantes y una lámina "lo que no probamos" |
| Sin notificaciones | Menos sensación de sistema vivo | Aviso de Telegram cuando falta la segunda firma |
| Sin URL pública fiable | El jurado no puede probar | Terminar Vercel, probar desde ventana limpia, botón de reinicio |
| Cifras sin alcance | Un "0 pagos indebidos" a secas descalifica en credibilidad | Decir "0 en N casos y M variantes" y listar lo no probado |

## 13. Diferenciadores a defender en el pitch
1. **El recibo de cada pago con su costo**: lectura, revisión humana, comisión del riel, cambio y parte de infraestructura, y lo que Kauta evitó pagar mal.
2. **Tres personas con doble firma** y el pago siempre a la cuenta registrada.
3. **Cascada de lectura** XML, texto, OCR, IA: la IA es la línea de costo más pequeña con las tarifas declaradas (la prueba lo recalcula con la IA ×10).

## 14. Plan hasta el congelamiento
| Prioridad | Tarea | Notas |
|---|---|---|
| 1 | Lectura real de una factura nueva con costo medido | Necesita clave |
| 2 | Evidencia de seguridad independiente | Verificador, ataque, lámina de límites |
| 3 | URL pública en Vercel y ensayo desde ventana limpia | Autorizar el origen exacto en la API |
| 4 | Aviso de Telegram por segunda firma pendiente | Bot con @BotFather |
| 5 | Video de 3 minutos en una sola historia | F12 y F10 con doble firma, aviso y costo del pago |
| 6 | Opcional: flujo animado y contador de dinero protegido | Solo si sobra tiempo |
Después de las 10:00 del domingo no se agrega nada.

## 15. Preguntas abiertas
- ¿Quién consigue la clave del modelo y cuándo?
- ¿Cuál es la URL final de Vercel y quién la publica?
- ¿Se permite tocar este repositorio para el verificador y el ataque, y quién los revisa?
- ¿Se conserva el set de 20 o se agregan casos para la evaluación independiente?
