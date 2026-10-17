# Requisitos de Kauta (lo que hace hoy)

Sirve para fijar, con evidencia, qué hace Kauta al 2026-10-17 (commit `7a9e108`) y qué decisiones y riesgos lo condicionan.
Fuentes: `aidlc-docs/inception/hechos-del-codigo.md` ("hechos §N"), `docs/PRD.md`, `kauta/README.md`, `docs/designs/kauta-estado-2026-10-17.md`. Todos los proveedores, documentos, costos y pagos son ficticios; no se mueve dinero real.
Lo que no se pudo comprobar va marcado NO DOCUMENTADO o NO VERIFICADO. Las pruebas no se ejecutaron para este documento.

## 1. Alcance

| Dentro | Fuera |
|---|---|
| Leer facturas (PDF, imagen, `.eml`, `.txt`, XML, ZIP), evaluar 13 reglas y decidir pagar, frenar o escalar | Mover dinero real, rieles reales (hechos §11, PRD §5) |
| Doble firma, pago simulado con wallet de doble partida, auditoría encadenada, libro de costos | Login real en la pantalla y activación de TOTP en pantalla (hechos §9) |
| Tres personas de demo (CFO, CEO, CTO) con permisos en el servidor | Servidor MCP, notificaciones por Telegram o correo (PRD §5 y §11) |
| API FastAPI, pantalla React, despliegue API + proxy de Vercel | Lectura con modelo en vivo durante la demo (simulada a propósito) |

## 2. Requisitos funcionales

| Id | Requisito | Evidencia |
|---|---|---|
| RF01 | Aceptar `.pdf .png .jpg .jpeg .webp .eml .txt .xml .zip`, máximo 10 MB, validación por bytes mágicos, nombre guardado como SHA-256 | hechos §9, §11; `rutas/negocio.py:25-47,126-139` |
| RF02 | Leer XML fiscal exacto sin IA (CFDI 4.0, UBL DIAN, contenedor DIAN, ZIP seguro) | hechos §11; `lectores_xml.py:351` |
| RF03 | Leer por cascada: XML, extracción de referencia (por nombre de archivo), rechazo de seguridad, texto del PDF u OCR Tesseract, IA solo si hay `ANTHROPIC_API_KEY` | hechos §11; `extractor.py:331-349` |
| RF04 | Normalizar moneda, monto y fecha; validar id fiscal (NIT, CC, CUIT, RFC, CNPJ, CPF, RUT, RUC, EIN) y datos bancarios (ABA, CLABE, CBU, IBAN) | hechos §3; `normalizacion.py:63-290` |
| RF05 | Evaluar las 13 reglas de forma pura y determinista, sin IA; los valores salen de la versión vigente de reglas | hechos §6; `motor.py:182-451` |
| RF06 | Agregar por precedencia: cualquier freno gana sobre escalar, y escalar sobre pagar; ante error inesperado, escalar (nunca pagar) | hechos §6; `motor.py:188-194,423-451` |
| RF07 | Calcular firmas requeridas: 0 si pagar, 1 si escalar y monto <= umbral, 2 si escalar y monto > umbral | hechos §8; `servicios/agente.py:154` |
| RF08 | Aprobar o rechazar una pendiente con comentario obligatorio, firma HMAC y re-evaluación del motor que bloquea si falla una regla dura | hechos §7; `agente.py:225-319` |
| RF09 | Segregación: quien carga no aprueba; no se firma dos veces; quien dispara una reevaluación no es la única firma | hechos §8; `agente.py:233-240,347-353` |
| RF10 | Pagar a la cuenta registrada del beneficiario, nunca a la del documento; confirmar titular, re-verificar firmas, saldo real, clave de idempotencia y un solo pago vivo por factura | hechos §7, §9; `pagos.py:141-220` |
| RF11 | Wallet de doble partida en USD (reserva, tránsito, comisión, costo FX, liquidación o devolución) | hechos §3, §7; `wallet.py:26-111` |
| RF12 | Catálogo de 8 rieles con comisión y spread FX (ACH, WIRE, SWIFT, SPEI, BREB, ACH_CO, PIX, USDC) | hechos §10; `pagos.py:37-71` |
| RF13 | Detectar cambio de cuenta (R07): crear solicitud pendiente que otra persona con método registrado debe verificar, y reevaluar | hechos §7, §9; `negocio.py:208-233` |
| RF14 | Reglas versionadas: editar 8 parámetros crea una versión nueva, ajusta la sub-wallet y reevalúa frenadas y pendientes sin pagar solo | hechos §4, §7; `negocio.py:247-271` |
| RF15 | Simular "qué pasaría si" con otros parámetros sin guardar | hechos §4; `negocio.py:274-288` |
| RF16 | Detectar instrucciones dirigidas al agente dentro del documento (10 patrones) y escalar por R13 | hechos §9; `extractor.py:38-42,160-162` |
| RF17 | Registro de auditoría con cadena HMAC-SHA256, verificable al leer y exportable a CSV o JSONL | hechos §3, §4; `auditoria.py:29-87`, `control.py:79-87` |
| RF18 | Libro de costos (`eventos_costo`) con lectura, revisión humana, comisión, cambio e infraestructura; desconocido no es cero | hechos §10; `costos.py`, `modelos.py:233-262` |
| RF19 | Recibo por factura con total completo o parcial y marca de "protegido" | hechos §10; `metricas.py:259-289` |
| RF20 | Métricas por rol (CFO, CEO, CTO) y vista Rendimiento con 4 tarjetas, todas marcadas `simulado: true` | hechos §10; `control.py:28-65` |
| RF21 | Simulador con 14 escenarios, factura sintética y simulación de 1 a 36 meses aislada, con verificador independiente de pagos | hechos §4, §13; `simulador.py:35,236-301` |
| RF22 | Siembra al arrancar: 15 beneficiarios, regla v1, wallet (120.000 USD en operativa, 15.000 trasladados a cxp) y las 20 facturas del set | hechos §14; `semilla.py:77-146` |
| RF23 | Preparar el recorrido de demo (presupuesto simulado USD 20.000 y primera firma de F10 por el CFO) con `KAUTA_PREPARAR_RECORRIDO=1` o desde el Simulador; auditado | `kauta/README.md:40-47`; hechos §14 |
| RF24 | Restablecer la demo (solo en modo demo, permiso del CTO) | hechos §4; `control.py:131-139` |
| RF25 | Comprobante PDF A5 simulado por pago | hechos §4; `dinero.py:95` |
| RF26 | Entrada a la pantalla por selector de persona sin contraseña (`POST /api/auth/persona`, solo en modo demo) con recuperación ante 401 y reintento ante 502 | hechos §9, §12; `auth.py:87-96`, `api.ts:178-185` |
| RF27 | Gestión de personas por API: invitar, registrar con código, cambiar rol, activar, desbloquear, cambiar contraseña; TOTP por API | hechos §4; `rutas/personas.py`, `auth.py:124-162` |
| RF28 | Pantalla de 11 rutas hash: resumen, facturas, detalle, pregunta, simulador, wallet, rendimiento, proveedores, reglas, auditoría, seguridad | hechos §12; `App.tsx:17-28` |
| RF29 | Reintentar un pago devuelto tras reevaluar (nuevo pago con `intento+1`) | hechos §7; `dinero.py:66-87` |
| RF30 | Procesar los 4 documentos "sorpresa" (CFDI, ZIP DIAN, XXE, nota crédito) sobre demanda | hechos §4, §15; `negocio.py:142-151` |

## 3. Requisitos no funcionales

| Id | Requisito | Evidencia |
|---|---|---|
| RNF01 | Falla cerrado: error o duda produce escalar o frenar, nunca pagar | hechos §6; `motor.py:188-194` |
| RNF02 | Sesión: token de 256 bits, solo su SHA-256 en base; 30 min de inactividad, 8 h máximo; cookie HttpOnly y SameSite=Strict (Secure con HTTPS) | hechos §9; `sesiones.py:30-46` |
| RNF03 | CSRF por cabecera en métodos que cambian datos y verificación de `Origin` | hechos §9; `sesiones.py:78-80`, `cabeceras.py:26-30` |
| RNF04 | Cabeceras: CSP estricta, nosniff, X-Frame-Options DENY, no-referrer, `Cache-Control: no-store` en `/api` | hechos §9; `cabeceras.py:19-45`, `web/vercel.json:16-55` |
| RNF05 | Cifrado en reposo AES-256-GCM de cuentas bancarias, secretos TOTP y cuentas nuevas | hechos §9; `cifrado.py:25-36` |
| RNF06 | Firmas HMAC-SHA256 de aprobaciones y órdenes de pago, re-verificadas antes de pagar | hechos §9; `firma.py`, `pagos.py:146-148` |
| RNF07 | Contraseñas con Argon2id, mínimo 15 caracteres, bloqueo tras 5 intentos por 15 min | hechos §9; `contrasenas.py`, `auth.py:23-24` |
| RNF08 | Límites de tasa por IP, cuenta o usuario en login, registro, carga y simulador (en memoria, por proceso) | hechos §9; `limites.py` |
| RNF09 | XML con `defusedxml` (sin DTD ni entidades) y ZIP con topes (25 MB, 20 archivos, 60 MB, razón 200) | hechos §9; `lectores_xml.py:39-43` |
| RNF10 | Salida escapada: sin `innerHTML` ni `dangerouslySetInnerHTML` en `web/src` | hechos §9 |
| RNF11 | Dinero con `NUMERIC(18,2)`; costos en nano USD enteros | hechos §5, §10; `modelos.py:24-25` |
| RNF12 | Un solo proceso del servidor (candado de hilos y limitador locales) | hechos §9, §14; `servicios/__init__.py:4-6` |
| RNF13 | Contenedor sin root, FS de solo lectura, `cap_drop ALL`; systemd con `ProtectSystem=strict` | hechos §9; `Dockerfile:13,25`, `ops/kauta.service:14-18` |
| RNF14 | Pruebas: 60 funciones, 76 casos (conteo por lectura de `def test_`); no se ejecutaron aquí (NO VERIFICADO en ejecución) | hechos §13; `kauta-estado-2026-10-17.md:9` |
| RNF15 | Explicabilidad: cada factura guarda motivo, tira de 13 reglas, versión de reglas y recibo | hechos §5, §10; `modelos.py:164-206` |

## 4. Decisiones vigentes

| Id | Decisión | Fuente |
|---|---|---|
| D-A | La IA lee, el código decide; el motor no usa IA | hechos §6; `motor.py:2-17` |
| D-B | Libro de costos como fuente única de recibos y métricas (enfoque B) | `kauta-finops-rediseno.md:77` |
| D-C | API y SQLite en el servidor propio; pantalla en Vercel con proxy `/api` | `kauta-estado-2026-10-17.md:14-19`, hechos §14 |
| D-D | Entrada por persona sin contraseña, solo demostración de permisos; la API de contraseñas e invitaciones se conserva por regresión (D8) | `kauta/README.md:7-9,129-130`; `kauta-estado-2026-10-17.md:78-81` |
| D-E | Lectura del set simulada (tabla de referencia) y costos de IA calculados con tarifa declarada | hechos §11; `kauta/README.md:36-38` |
| D-F | F10 usa preparación opcional y auditada; el set oficial no se modifica y las reglas duras no se saltan | `kauta-estado-2026-10-17.md:21-24` |
| D-G | GitHub Actions diferido a TODO (D15) | `TODOS.md:5-15` |

## 5. Riesgos y límites (hechos §9, §14, §17)

| Riesgo | Efecto | Estado |
|---|---|---|
| Candado y limitador locales al proceso | No sirve con varios procesos; concurrencia entre procesos sin resolver | Documentado como un solo worker |
| Sin migraciones (solo `create_all`) | Cambiar el esquema exige recrear la base | Sin mitigación |
| Sin CI | Una prueba en rojo puede llegar a Vercel sin aviso | Pendiente (`TODOS.md`) |
| Tabla `idempotencia` sin uso | La idempotencia real vive en `pagos.clave_idempotencia` | Hecho §5 |
| Costos de IA simulados; las llamadas reales no registran tokens | El costo de IA real no se mide | Hecho §11 |
| Costo de lectura deducido de extensión y confianza, no del lector usado | El desglose XML/texto/OCR/IA puede no reflejar el lector real | Hecho §17 #12 |
| Pantalla sin login: en modo producción `/api/auth/persona` responde 404 (`auth.py:95-96`) y la pantalla no tiene otra entrada | La pantalla no es utilizable en producción tal como está. El modo del servidor desplegado es NO VERIFICADO | Hecho §17 #17 |
| URL de Vercel sin confirmar; sin ella las firmas responden 403 | El jurado no puede probar desde Vercel | Pendiente de persona |
| Sin rotación de claves ni KMS | Cambiar el id de clave rompe el descifrado | Hecho §9 |
| Auditoría y libro "solo inserción" sin mecanismo de base; `restablecer` las borra en demo | La inmutabilidad se detecta por verificación, no se impide | Hecho §5 |
| Sin verificador independiente ni evaluación adversarial publicada | Cifras de seguridad sin alcance | `PRD.md` §10 y §12 |
| Reloj fijo de `vistas.plazo` (2026-10-17) | Los plazos de octubre 2026 no usan la fecha real | Hecho §17 #15 |

## 6. Cifras con su alcance

| Cifra | Alcance |
|---|---|
| Set de 20: 9 pagar, 5 frenar, 6 escalar | Esperado en `data/esperado.csv`; la coincidencia en ejecución la comprueba `test_set_oficial_20_de_20` (no ejecutada aquí) |
| 76 casos de prueba | Conteo por lectura del código; coincide con el documento de estado |
| 0 pagos fuera de reglas | Solo sobre el set y el estrés de las pruebas; no hay evaluación independiente. No usar sin decir "en N casos" |
