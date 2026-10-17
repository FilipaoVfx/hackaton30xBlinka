# Guion de la demostración (3 minutos)

Sirve para grabar el video con el recorrido F01, F07, F12, F10 de `kauta/README.md:49-58`. Fuentes: `kauta/README.md`, `data/esperado.csv`, `docs/PRD.md` §8 y §14, `hechos-del-codigo.md`. Fecha: 2026-10-17.
Los tiempos por escena son una propuesta de este guion (NO VERIFICADO con cronómetro). Nada de esto se ejecutó en el navegador para este documento. Todo es ficticio y sin dinero real.

## Preparación
| Paso | Cómo | Evidencia |
|---|---|---|
| Datos del recorrido | Arrancar con `KAUTA_PREPARAR_RECORRIDO=1`, o CTO > Simulador > Restablecer la demo > "Con las 20 facturas del set" | `kauta/README.md:40-47` |
| Efecto | Presupuesto simulado USD 20.000 y primera firma de F10 por Carlos; la segunda queda pendiente del CEO | `kauta/README.md:43-45` |
| No definir | `ANTHROPIC_API_KEY`: la extracción del set y los costos de IA son simulados | `kauta/README.md:37-38` |
| Entrada | La app abre como CFO; se cambia de persona sin contraseña | `App.tsx:36-43` |

## Escenas

| Tiempo (propuesto) | Pantalla | Qué se ve | Qué decir |
|---|---|---|---|
| 0:00-0:20 | CFO > Resumen | Cuatro métricas del dinero (pagado, esperando firma, costo, dinero protegido) y las facturas que necesitan su firma | La IA lee, el código decide. Datos ficticios |
| 0:20-0:50 | Facturas > F01 | Pago automático de USD 850 (Nube Clara), motivo, tira de 13 reglas en cumplimiento y recibo de costos | Cumple las 13 reglas: paga sin persona (0 firmas) |
| 0:50-1:15 | Facturas > F07 | Recordatorio de la misma INV-1001, frenada por R03 sin pago; suma a dinero protegido | Un duplicado no se paga dos veces |
| 1:15-1:55 | Pregunta o F12 | Chat de Andrés Rojas, COP 4.800.000 (USD 1.500 a tasa 3.200 de `reglas.json`), cuenta 0093 frente a ···8152; pide confirmar vencimiento y cuenta por un canal independiente; comentar y aprobar | Kauta paga a la cuenta registrada ···8152, nunca a la que pide el documento |
| 1:55-2:20 | Rendimiento | Cuatro tarjetas y desglose de lectura XML/texto/OCR/IA desde el mismo libro de los recibos | Costos simulados; "—" es desconocido, no cero |
| 2:20-2:50 | Cambiar a CEO > F10 | Datos del Sur, USD 3.200 sobre el umbral de 3.000: primera firma de Carlos ya puesta; segunda firma y pago | Dos firmas; las reglas duras se verifican otra vez antes de pagar |
| 2:50-3:00 | Auditoría o Seguridad | Cadena de auditoría verificada | Lo que no hacemos: ver "Lo que no se muestra" |

## Cifras y su alcance

| Cifra | Alcance | Evidencia |
|---|---|---|
| 9 pagar, 5 frenar, 6 escalar | Esperado del set de 20 (`esperado.csv`); la coincidencia en ejecución es NO VERIFICADO aquí | `esperado.csv:2-21`; hechos §15 |
| 13 reglas, umbral USD 3.000, máximo por pago USD 10.000, presupuesto USD 15.000 (USD 20.000 con la preparación) | Valores de la versión 1 de reglas | `reglas.json:17-21`; `kauta/README.md:43` |
| 76 pruebas | Conteo por lectura del código; no ejecutadas | hechos §13 |
| Dinero protegido, costo por factura resuelta | Calculados en vivo por el libro de costos; el valor exacto en pantalla es NO DOCUMENTADO | hechos §10 |
| "0 pagos indebidos" | Solo decirlo como "0 en el set de 20 y las pruebas del repositorio"; no hay evaluación independiente | `PRD.md` §12 |

## Riesgos de la grabación
| Riesgo | Mitigación |
|---|---|
| F10 sin preparación devuelve 409 por R12 al aprobar | Ejecutar la preparación antes de grabar |
| Sin URL de Vercel autorizada, el selector y las firmas dan 403 | Grabar contra la API local o autorizar el origen en `KAUTA_ORIGENES_ADICIONALES` |
| Demo en el servidor propio: el modo (demo o producción) es NO VERIFICADO; en producción el selector da 404 | Confirmar el modo antes del ensayo |
| El recorrido debe poder reiniciarse | CTO > Restablecer la demo |

## Lo que no se muestra
- Lectura con modelo en vivo (simulada; requiere clave, pendiente de persona).
- Aviso por Telegram o correo (no existe).
- Verificador independiente y ataque con variantes (pendientes, `PRD.md` §14).
