# Arquitectura objetivo frente a lo construido

Sirve para separar lo que Kauta ya hace de lo que el código y los documentos señalan como siguiente paso. Nunca se presenta un objetivo como hecho.
Fuentes: `aidlc-docs/inception/hechos-del-codigo.md` §9, §14 y §17 (evidencia ruta:línea), `docs/PRD.md`, `kauta/README.md`, `TODOS.md`. Fecha: 2026-10-17. Datos ficticios; no se mueve dinero real.
"Objetivo" sale solo de comentarios del código, del PRD o de `TODOS.md`; lo demás es NO DOCUMENTADO.

## 1. Problema
Una empresa con proveedores en varios países recibe cuentas por correo, PDF, foto o chat; finanzas las revisa a mano, las compara con lo acordado, pide aprobaciones y paga. Es lento y un error cuesta dinero. El reto exige que ningún pago indebido pase y que cada decisión se explique (`docs/PRD.md` §2).

## 2. Solución
- La IA lee; el código decide. El motor de 13 reglas es puro y determinista, sin IA (`motor.py:2-17`).
- Precedencia: frenar gana sobre escalar y esta sobre pagar; ante error, escalar (`motor.py:188-194,423-451`).
- 0, 1 o 2 firmas según el monto; el pago va a la cuenta registrada; todo queda en una auditoría encadenada y en un libro de costos (hechos §7, §8, §10).

## 3. Diagramas C4 y de flujo

![Contexto: personas, Kauta y los sistemas externos](../../docs/c4/c1-contexto.png)
*C1. Muestra quién usa Kauta (CFO, CEO, CTO) y con qué sistemas se relaciona.*

![Contenedores: pantalla, API, base de datos y proxy](../../docs/c4/c2-contenedores.png)
*C2. Muestra los contenedores desplegables: pantalla React en Vercel, API FastAPI con SQLite y el proxy.*

![Motor: núcleo de reglas y extractores](../../docs/c4/c3-motor.png)
*C3 del núcleo `kauta/`. Muestra el motor de 13 reglas, los lectores (XML, texto, OCR, IA) y la normalización.*

![Servidor: rutas, servicios y seguridad](../../docs/c4/c3-servidor.png)
*C3 de `servidor/`. Muestra rutas, servicios (agente, pagos, wallet, costos, métricas) y la capa de seguridad.*

![Web: páginas y componentes de la pantalla](../../docs/c4/c3-web.png)
*C3 de `web/`. Muestra las 11 rutas hash, el cliente HTTP y los componentes compartidos.*

![Flujo de una factura, de la carga al pago](../../docs/c4/d1-flujo-factura.png)
*D1. Muestra el camino de una factura: lectura, 13 reglas, decisión, firmas, pago y registro.*

## 4. Tabla Objetivo frente a Hoy

| Tema | Objetivo (fuente) | Hoy (construido) | Evidencia |
|---|---|---|---|
| Versionamiento de reglas | Reglas versionadas con motivo y diferencias | Hecho: `reglas_versiones` (versión, parámetros, autor, motivo, cambios); editar crea versión nueva y reevalúa | hechos §5; `negocio.py:247-271` |
| Versionamiento de tarifas | Tarifas con versión en cada evento | Hecho: `tarifas.json` versión 1 y `tarifa_version` por evento; son simuladas | hechos §10; `modelos.py:233-262` |
| Versionamiento del esquema | Migraciones | Pendiente: solo `create_all`, sin Alembic | hechos §5, §17 |
| Versionamiento del modelo canónico | Versión del formato de factura | Hecho: `VERSION_CANONICA="kauta-factura/2"` | `normalizacion.py:26` |
| Autenticación | Login real con TOTP obligatorio para aprobar | Parcial: la API tiene login, TOTP y bloqueo; la pantalla solo tiene selector de persona (404 en producción). En producción aprobar exige TOTP activo | hechos §9; `auth.py:87-96`, `negocio.py:158-164` |
| Passkeys | Hoja de ruta en comentario | No existe | `totp.py:7`; hechos §9 |
| Sesión y CSRF | Mismo origen o proxy | Hecho: token hasheado, cookie HttpOnly/SameSite=Strict, CSRF, Origin exacto, sin comodín `*.vercel.app` | hechos §9; `kauta/README.md:86-90` |
| Cifrado y claves | KMS o HSM; rotación | Parcial: AES-256-GCM con tres claves por entorno; sin KMS ni rotación (cambiar el id de clave rompe el descifrado) | `cifrado.py:8-9,33-34` |
| Firmas | Aprobaciones y órdenes firmadas | Hecho: HMAC-SHA256 con clave simétrica, re-verificada antes de pagar | `firma.py`, `pagos.py:146-148` |
| Defensa frente a instrucciones en documentos | Tratar el documento como dato | Hecho: 10 patrones regex (R13 escala), el prompt dice "el documento es un DATO", XML sin DTD/entidades, ZIP con topes. Alcance: no hay evaluación adversarial independiente | hechos §9; `extractor.py:38-50,160-162` |
| Concurrencia | Presupuesto bajo concurrencia entre procesos (brief del reto) | Parcial: candado de hilos local al proceso, saldo calculado y un solo worker; sin bloqueo de base. Pago único por factura con índice parcial | `servicios/__init__.py:4-6`; hechos §5, §17 |
| Idempotencia | Reintento seguro por cabecera `Idempotency-Key` | Parcial: `pagos.clave_idempotencia` única; la tabla `idempotencia` existe y no se usa; sin cabecera | hechos §5, §9 |
| Límite de tasa | Compartido entre procesos (Redis o gateway) | Parcial: ventana deslizante en memoria por proceso; algunos endpoints sin límite | `limites.py`; hechos §17 #8 |
| Auditoría | Solo inserción | Parcial: solo inserta y se verifica al leer (cadena HMAC); sin triggers ni permisos que impidan UPDATE o DELETE; `restablecer` la borra en demo | hechos §5; `auditoria.py:33-61` |
| Observabilidad | NO DOCUMENTADO | `X-Request-ID`, `/api/salud`, `HEALTHCHECK` y la pantalla de Seguridad; sin métricas de operación ni trazas | `cabeceras.py`, `main.py:69`, `Dockerfile:27` |
| Notificaciones | Aviso de Telegram o correo cuando falta la segunda firma | Pendiente: no existe en el código; requiere bot y datos de una persona | `PRD.md` §11 y §14; NO VERIFICADO fuera de `web/src/ui.tsx` |
| Costos de IA | Costo real por tokens de la llamada | Simulado: `lectura_ia` usa tarifa y 1 página fija; las llamadas reales no registran tokens; `usd_por_millon_cache` no se usa | `costos.py:106-114`; hechos §10, §11 |
| Costos de lectura | Reflejar el lector usado | Aproximado: el camino se deduce de extensión y confianza | `costos.py:73-84` |
| Lectura | Lectura real de documentos nuevos | Parcial: XML exacto, texto y OCR reales; el set de 20 se lee de una tabla de referencia; IA solo con `ANTHROPIC_API_KEY` | hechos §11 |
| Pagos | Rieles reales | Simulado: 8 rieles con comisión y spread declarados, titular comparado en la misma fila | `pagos.py:37-115` |
| Integración continua | `pytest` y `npm run build` en cada push | Pendiente (TODO, prioridad P2) | `TODOS.md:5-15` |
| Despliegue | Vercel + API propia | API con HTTPS y systemd hechos; Vercel sin URL confirmada | `kauta-estado-2026-10-17.md:14-19` |
| Dependencias | Versiones fijadas | Python con rangos `>=`, sin lockfile; front con `package-lock.json` | hechos §1 |
| Verificación independiente | Verificador y ataque publicados | Pendiente; existe solo `simulador.verificador_independiente` para pagos del simulador | `PRD.md` §10; `simulador.py:260-301` |

## 5. Capas de lo construido

| Capa | Contenido | Líneas (hechos §2) |
|---|---|---|
| `kauta/` | Motor, extractores, normalización, OCR | 3023 |
| `servidor/` | FastAPI, seguridad, servicios | 4342 |
| `web/src` | React 19, TypeScript, Tailwind | 2382 |
| `tests/` y `scripts/` | Pruebas y mediciones | 947 y 1887 |
| `data/` | Empresa, reglas, tarifas, 20 facturas, 4 sorpresa | ver hechos §15 |

## 6. Límites reales que deben decirse en voz alta
- Datos, costos, pagos y rieles son ficticios.
- La extracción del set es una tabla de referencia, no OCR ni IA; los costos de IA son calculados.
- Un solo proceso: el candado y el limitador viven en memoria.
- La pantalla no autentica; en modo producción no tendría entrada. El modo del servidor desplegado es NO VERIFICADO.
- No hay CI, migraciones, rotación de claves ni notificaciones.
