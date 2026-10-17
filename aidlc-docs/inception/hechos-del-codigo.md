# Ficha de hechos del código de Kauta

Fecha de lectura: 2026-10-17. Commit leído: `7a9e108` (rama `main`, único cambio sin versionar: `docs/PRD.md`).
Convención: las rutas son relativas a `kauta/` salvo que digan `../`. Formato de evidencia: `ruta:línea`.
Regla de esta ficha: solo lo que está en el código; lo que no está dice NO ENCONTRADO. No se ejecutó la app ni las pruebas: los conteos de pruebas salen de leer `def test_`.
"Documento" = README, DESIGN.md, docs/. Donde difieren del código se anota en la sección 17.

---

## 1. Stack y versiones

| Pieza | Versión / valor | Evidencia |
|---|---|---|
| Python (imagen) | 3.12-slim | `Dockerfile:11` |
| Node (imagen y motor) | 22 (alpine; `engines` 22.x; `.nvmrc` 22) | `Dockerfile:3`, `web/package.json:29-31`, `web/.nvmrc:1` |
| Servidor | fastapi>=0.120, uvicorn[standard]>=0.32, sqlalchemy>=2.0, pydantic>=2.8, python-multipart>=0.0.12 | `requirements-servidor.txt:2-6` |
| Seguridad | argon2-cffi>=23.1, cryptography>=43, pyotp>=2.9, segno>=1.6 (QR del TOTP), defusedxml>=0.7 | `requirements-servidor.txt:7-8,9,10,11` |
| Documentos | pypdf>=5.0, pypdfium2>=4.0, pillow>=10.0, reportlab>=4.0 (comprobante PDF) | `requirements-servidor.txt:12-15` |
| IA | anthropic>=1.0; modelo por defecto `claude-sonnet-5-5` (variable `KAUTA_MODELO`) | `requirements-servidor.txt:16`, `kauta/extractor.py:33` |
| PostgreSQL | psycopg[binary]>=3.2 (opcional); imagen `postgres:17-alpine` | `requirements-servidor.txt:17`, `docker-compose.yml:18` |
| OCR | Tesseract (paquete del sistema, no Python), idiomas `spa+eng`; opencv opcional comentado | `requirements-servidor.txt:18-25`, `kauta/ocr.py:30`, `Dockerfile:15-17` |
| Pantalla de respaldo | streamlit>=1.50,<2 | `requirements.txt:3` |
| Pruebas | pytest>=8.0, `httpx2>=2.0` (comentado "cliente de pruebas de Starlette/FastAPI"), python-stdnum>=2.0, clabe>=2.1 | `requirements.txt:4-7` |
| Front | react ^19.3.1, react-dom ^19.3.1, lucide-react ^1.59.0, @fontsource-variable/inter ^5.2.8 | `web/package.json:13-18` |
| Front (dev) | vite ^8.3.4, @vitejs/plugin-react ^6.1.2, tailwindcss ^4.3.3 + @tailwindcss/vite ^4.3.3, typescript ~5.9.3, playwright ^1.64.1 | `web/package.json:19-28` |
| Versión de la app | web `2.0.0`; servidor `2.1.0` | `web/package.json:4`, `servidor/config.py:58` |
| Scripts npm | `dev`=vite, `build`=vite build, `typecheck`=tsc --noEmit, `preview`, `test:e2e`=node ../scripts/probar_web.mjs | `web/package.json:6-12` |
| Vite | puerto 5173, proxy `/api` a `http://127.0.0.1:8000`, salida `dist`, sin sourcemap | `web/vite.config.ts:9-10` |
| TypeScript | strict, target ES2022, jsx react-jsx | `web/tsconfig.json:3-8` |
| Vercel | framework vite; build `npm run typecheck && npm run build`; output `dist`; install `npm ci` | `web/vercel.json:3-5,57` |
| Vercel rewrites | `/api/:path*` a `https://kauta.2-25-233-186.sslip.io/api/:path*`; resto a `/index.html` | `web/vercel.json:6-14` |
| Vercel cabeceras | nosniff, X-Frame-Options DENY, Referrer-Policy no-referrer, CSP estricta (`default-src 'self'`...), `/api` Cache-Control no-store, `/assets` immutable 1 año | `web/vercel.json:16-55` |
| Docker | 2 etapas: node:22-alpine compila web; python:3.12-slim corre `uvicorn servidor.main:app --host 0.0.0.0 --port 8000 --proxy-headers --no-server-header`, usuario `kauta` uid 10001 | `Dockerfile:3-28` |
| Docker Compose | servicio `kauta` (8000:8000, `read_only`, `cap_drop ALL`, `no-new-privileges`) + `db` postgres; `KAUTA_BD=postgresql+psycopg://...` | `docker-compose.yml:3-25` |

Lockfile front: `web/package-lock.json` (1676 líneas). No hay lockfile de Python (solo rangos `>=`): NO ENCONTRADO.
CI (GitHub Actions): NO ENCONTRADO; `../TODOS.md:5-15` lo lista como pendiente.

---

## 2. Árbol de carpetas y líneas por archivo

Totales (solo `.py`/`.mjs` versionados): `kauta/` 3023, `servidor/` 4342, `tests/` 947, `scripts/` 1887. `web/src` (ts, tsx, css) 2382. `app.py` 436.

```
kauta/
  app.py                       436  pantalla Streamlit (plan B)
  Dockerfile 28 · docker-compose.yml 28 · .env.example 15 · DESIGN.md 46 · README.md 133
  kauta/                        (núcleo, sin FastAPI)
    __init__.py 2 · agente.py 201 · extractor.py 397 · lectores_xml.py 562
    motor.py 478 · normalizacion.py 580 · ocr.py 526 · registro.py 69 · ui.py 208
  servidor/
    __init__.py 1 · config.py 87 · db.py 37 · esquemas.py 149 · main.py 82 · modelos.py 372 · vistas.py 116
    rutas/      __init__ 1 · auth 182 · control 139 · dinero 143 · negocio 288 · personas 91 · simulador 48
    seguridad/  __init__ 1 · cabeceras 46 · cifrado 41 · contrasenas 48 · firma 32 · limites 41 · permisos 57 · sesiones 96 · totp 45
    servicios/  __init__ 6 · agente 377 · auditoria 75 · costos 133 · metricas 368 · pagos 235 · semilla 195 · simulador 435 · usuarios 264 · wallet 111
  web/
    index.html 16 · vite.config.ts 11 · vercel.json 58 · tsconfig.json 19 · package.json 32
    src/  main.tsx 13 · App.tsx 139 · api.ts 273 · ui.tsx 364 · styles.css 160
    src/pages/  Auditoria 59 · Detalle 300 · Facturas 145 · Pregunta 66 · Proveedores 126 · ReciboFactura 18
                Reglas 131 · Rendimiento 29 · Resumen 39 · Seguridad 15 · Simulador 345 · Wallet 160
  scripts/  capturas_web.py 75 · contrastar_validadores.py 143 · correr_set.py 67 · empaquetar.py 61
            generar_set.py 1221 · medir_extraccion.py 74 · medir_ocr.py 77 · probar_web.mjs 157 · probar_web.py 12
  tests/    conftest.py 22 · test_costos.py 100 · test_formatos.py 169 · test_kauta.py 194 · test_servidor.py 462
  ops/      kauta.service 21 · nginx.kauta 27
  data/     empresa.json 14 · reglas.json 22 · tarifas.json 11 · beneficiarios.json 282 · esperado.csv 21
            referencia_extracciones.json 563 · facturas/ (20 archivos) · previews/ (14 PNG) · sorpresa/ (4 archivos + esperado_sorpresa.csv 5)
  assets/ (5 imágenes) · static/fonts/ (6 .otf Inter + licencia) · .vscode/ (4 archivos)
../  README.md 243 (brief del reto) · TODOS.md 17 · docs/PRD.md 109 (sin versionar) · docs/designs/ (2 .md) · prototipos/ (4 HTML, 432 líneas)
```

`web/dist/` no existe en el repositorio (`.gitignore:17`; `README.md:20`).

---

## 3. Módulos de `kauta/` y `servidor/`

### `kauta/` (núcleo)

| Módulo | Responsabilidad | Públicos principales |
|---|---|---|
| `motor.py` | Evalúa las 13 reglas de forma pura y determinista; no usa IA (`motor.py:2-17`) | `CATALOGO:29`, `PRIORIDAD_FRENAR:45`, `PRIORIDAD_ESCALAR:46`, `evaluar:182`, `_evaluar:197`, `buscar_beneficiario:147`, `periodo_de:165`, `clave_beneficiario:172`, `monto_en_usd:138`, `fmt_dinero:99`, `Decision:75`, `ResultadoRegla:66` |
| `extractor.py` | Lee un archivo (PDF, imagen, .eml, .txt, XML, ZIP) y devuelve extracción + hashes + texto | `leer_documento:135`, `extraer_xml:220`, `extraer_ocr:235`, `enriquecer:279`, `detectar_instrucciones:160`, `normalizar:173`, `ExtractorReferencia:323`, `ExtractorIA:352`, `ExtraccionNoDisponible:319`, `PROMPT_SISTEMA:44` |
| `lectores_xml.py` | Lee XML fiscal exacto sin IA (CFDI 4.0, UBL DIAN, contenedor DIAN), ZIP seguro, QR/CUFE/CAE | `leer_xml_fiscal:351`, `parsear_xml:98`, `abrir_zip:372`, `leer_cfdi:130`, `leer_ubl_dian:242`, `leer_contenedor_dian:319`, `identificadores_fiscales:443`, `contrastar:469`, `DocumentoRechazado:67` |
| `normalizacion.py` | Validadores fiscales/bancarios, normalización de moneda, monto, fecha; modelo canónico | `validar_id_fiscal:217`, `validar_nit/cc/cuit/rfc/cnpj/cpf/rut/ruc/ein` (`:63-188`), `validar_aba:230`, `validar_clabe:238`, `validar_cbu:248`, `validar_iban:290`, `normalizar_monto:383`, `normalizar_fecha:411`, `normalizar_moneda:360`, `FacturaCanonica:489`, `VERSION_CANONICA="kauta-factura/2":26` |
| `ocr.py` | Lector local: texto incrustado del PDF u OCR con Tesseract, y extracción de campos por patrones | `leer:498`, `campos_desde_texto:423`, `disponible:56`, `leer_imagen:161`, `leer_pdf:170`, `MAX_PAGINAS=5:34` |
| `agente.py` | Agente en memoria (versión Streamlit/pruebas legado): extrae, evalúa, registra, aprueba | `Agente:30` (`procesar:40`, `aprobar:63`, `rechazar:102`, `reevaluar:123`, `metricas:141`) |
| `registro.py` | Registro de auditoría en archivo JSONL con cadena SHA-256 (usado por el agente en memoria) | `Registro:27` (`agregar:36`, `verificar:52`, `a_csv:61`) |
| `ui.py` | HTML/CSS para Streamlit | `badge`, `kpi`, `tarjeta_factura`, `lista_reglas` (`:104-158`) |

Los módulos `kauta/agente.py`, `kauta/registro.py`, `kauta/ui.py` solo los importan `app.py` y `tests/test_kauta.py` (`app.py:20-23`, `tests/test_kauta.py:28-30`); el servidor no los usa (`servidor/main.py` y `servicios/agente.py:27-28` importan solo `motor` y `extractor`).

### `servidor/`

| Módulo | Responsabilidad | Públicos principales |
|---|---|---|
| `main.py` | Crea la app FastAPI, monta routers, middlewares, sirve `web/dist` | `app:38`, `LimiteCuerpo:44`, `/api/salud:69`, `pantalla:78` |
| `config.py` | Config desde variables de entorno; claves | `Config:45`, `cargar:70`, `CONFIG:87`, `_clave:27` |
| `db.py` | Motor SQLAlchemy (SQLite WAL/FK en demo) | `motor_bd:12`, `SesionBD:28`, `Base:31`, `obtener_bd:35` |
| `modelos.py` | Tablas (ver sección 5) | 16 clases `Base` |
| `esquemas.py` | Entradas Pydantic (`extra="forbid"`) | `ReglasIn:61`, `AprobarIn:51`, `SimFacturaIn:78`, `Estricto:18` |
| `vistas.py` | Convierte filas a JSON de la API | `factura_resumen:27`, `factura_detalle:78`, `preguntas:41`, `plazo:64` |
| `rutas/*` | Endpoints HTTP (sección 4) | un `APIRouter` `r` por archivo |
| `seguridad/permisos.py` | Roles y permisos | `ROLES:10`, `tiene:49`, `permisos_de:54` |
| `seguridad/sesiones.py` | Sesiones, CSRF, dependencia `requiere` | `crear:38`, `contexto:69`, `requiere:90` |
| `seguridad/cabeceras.py` | Cabeceras de seguridad y verificación de Origin | `CabecerasSeguridad:24`, `CSP:19` |
| `seguridad/cifrado.py` | AES-256-GCM con AAD | `cifrar:25`, `descifrar:31`, `enmascarar:39` |
| `seguridad/firma.py` | HMAC-SHA256 de aprobaciones y órdenes | `firmar:22`, `verificar:26`, `huella:30`, `canonico:18` |
| `seguridad/contrasenas.py` | Argon2id y política | `hashear:25`, `verificar:29`, `problemas_politica:40` |
| `seguridad/totp.py` | TOTP RFC 6238 con anti-repetición | `nuevo_secreto:20`, `verificar_codigo:32` |
| `seguridad/limites.py` | Límite de tasa en memoria (ventana deslizante) | `Limitador:14`, `limitar:38` |
| `servicios/agente.py` | Orquesta extracción, motor, pago, aprobaciones, reevaluación | `procesar_archivo:131`, `registrar:137`, `aprobar:225`, `rechazar:303`, `reevaluar:324`, `ExtractorServidor:47`, `ErrorNegocio:40` |
| `servicios/pagos.py` | Simulador de pagos: rieles, cotización, firmas, línea de tiempo | `RIELES:37`, `cotizar:94`, `confirmar_titular:112`, `crear_y_ejecutar:141`, `verificar_aprobaciones:125` |
| `servicios/wallet.py` | Libro mayor de doble partida en USD | `CUENTAS:26`, `transferir:59`, `saldo:65`, `verificar_libro:75`, `asegurar_fondeo:93` |
| `servicios/auditoria.py` | Cadena HMAC-SHA256 en la tabla `auditoria` | `registrar:33`, `verificar:50`, `exportar:64` |
| `servicios/costos.py` | Escribe eventos de costo (libro FinOps) | `registrar_lectura:87`, `registrar_revision:118`, `registrar_pago:128`, `camino_lectura:73`, `tarifas:34` |
| `servicios/metricas.py` | Calcula métricas y recibos desde el libro | `base:52`, `Libro:114`, `rendimiento:296`, `recibo:320`, `lente:338`, `esperando_firma:332` |
| `servicios/simulador.py` | Escenarios, factura sintética y simulación de años | `ESCENARIOS:35`, `crear_factura:236`, `verificador_independiente:260`, `simular_anio:359` |
| `servicios/semilla.py` | Crea datos de la demo, restablece, prepara recorrido | `iniciar:140`, `restablecer:153`, `preparar_recorrido:165`, `USUARIOS_DEMO:29`, `CONTRASENA_DEMO:28`, `PAGO:35` |
| `servicios/usuarios.py` | Invitaciones, registro, cambio de rol, activación | `invitar:59`, `registrar:102`, `cambiar_rol:145`, `activar:164`, `DIAS_INVITACION=7:29` |
| `servicios/__init__.py` | Candado global del proceso | `BLOQUEO = threading.RLock():6` |

---

## 4. API

Todas bajo prefijo `/api`. "Permiso" = argumento de `requiere(...)` (`seguridad/sesiones.py:90-96`). `ver` lo cumple cualquier rol que tenga al menos un permiso (`permisos.py:51`). Métodos que cambian datos exigen cabecera `X-CSRF-Token` (`sesiones.py:78-80`).

| Método | Ruta | Permiso | Qué hace | Evidencia |
|---|---|---|---|---|
| GET | `/api/salud` | ninguno | `{ok, version, modo}` | `main.py:69` |
| POST | `/api/auth/login` | ninguno | Correo+contraseña (+TOTP si activo); crea sesión | `rutas/auth.py:33` |
| POST | `/api/auth/logout` | ninguno | Revoca la sesión | `auth.py:75` |
| GET | `/api/auth/yo` | sesión | Usuario actual, modo, versión | `auth.py:82` |
| POST | `/api/auth/persona` | ninguno; solo `demo` (404 en producción) | Entra como una de las 3 personas sin contraseña | `auth.py:87-96` |
| GET | `/api/auth/demo` | ninguno; solo `demo` | Lista las 3 personas y la contraseña de demo | `auth.py:114-121` |
| POST | `/api/auth/mfa/iniciar` | sesión | Genera secreto TOTP y QR | `auth.py:124` |
| POST | `/api/auth/mfa/confirmar` | sesión | Activa TOTP | `auth.py:137` |
| POST | `/api/auth/mfa/desactivar` | sesión | Desactiva TOTP con código | `auth.py:152` |
| GET | `/api/auth/sesiones` | sesión | Sesiones activas propias | `auth.py:165` |
| DELETE | `/api/auth/sesiones/{prefijo}` | sesión | Revoca una sesión propia (prefijo >= 8) | `auth.py:175-178` |
| GET | `/api/facturas` | `ver` | Lista (filtros `estado`, `q`) | `rutas/negocio.py:50` |
| GET | `/api/facturas/{fid}` | `ver` | Detalle | `negocio.py:62` |
| GET | `/api/facturas/{fid}/recibo` | `ver` | Recibo de costos | `negocio.py:70` |
| GET | `/api/facturas/{fid}/vista` | `ver` | PNG re-codificado de la vista previa | `negocio.py:79` |
| POST | `/api/facturas/cargar` | `facturas.cargar` | Sube y procesa un archivo (10 MB; 30/min por usuario) | `negocio.py:126-139` |
| POST | `/api/facturas/sorpresa` | `facturas.cargar` | Procesa `data/sorpresa/S0*` no procesados | `negocio.py:142-151` |
| POST | `/api/facturas/{fid}/aprobar` | `facturas.aprobar` | Firma de aprobación (pide TOTP si el usuario lo tiene; en producción exige TOTP) | `negocio.py:154-169` |
| POST | `/api/facturas/{fid}/rechazar` | `facturas.aprobar` | Rechaza una pendiente | `negocio.py:172-177` |
| GET | `/api/aprobaciones` | `ver` | Bandeja de pendientes con preguntas, plazo, `ya_aprobe`, `cargue_yo` | `negocio.py:180-193` |
| GET | `/api/proveedores` | `ver` | Beneficiarios | `negocio.py:197` |
| GET | `/api/cambios-cuenta` | `ver` | Solicitudes de cambio de cuenta | `negocio.py:202` |
| POST | `/api/cambios-cuenta/{cid}/verificar` | `cuentas.verificar` | Aprueba/rechaza el cambio; quien lo pidió no puede verificarlo; reevalúa | `negocio.py:208-233` |
| GET | `/api/reglas` | `ver` | Reglas vigentes, catálogo, versiones | `negocio.py:237` |
| PUT | `/api/reglas` | `reglas.editar` | Crea versión nueva (8 parámetros), ajusta sub-wallet, reevalúa | `negocio.py:247-271` |
| POST | `/api/reglas/simular` | `ver` | "¿Qué pasaría si?" sobre frenadas y pendientes, sin guardar | `negocio.py:274-288` |
| GET | `/api/wallet` | `ver` | Saldos, periodos, libro, últimos 40 asientos | `rutas/dinero.py:20` |
| POST | `/api/wallet/fondear` | `wallet.fondear` | Depósito simulado a la cuenta operativa (<= 1.000.000) | `dinero.py:42`, `esquemas.py:110-111` |
| GET | `/api/pagos` | `ver` | Lista de pagos | `dinero.py:53` |
| GET | `/api/pagos/{pid}` | `ver` | Un pago | `dinero.py:58` |
| POST | `/api/pagos/{pid}/reintentar` | `pagos.reintentar` | Reintenta un pago `devuelto` tras reevaluar | `dinero.py:66-87` |
| GET | `/api/pagos/{pid}/comprobante` | `ver` | PDF A5 simulado | `dinero.py:95` |
| GET | `/api/rieles` | `ver` | Catálogo de rieles | `dinero.py:90` |
| GET | `/api/resumen` | `ver` | Métricas, lente por rol, serie, criterios | `rutas/control.py:28` |
| GET | `/api/rendimiento` | `ver` | Tarjetas de costo (parámetro `periodo`) | `control.py:61` |
| GET | `/api/auditoria` | `auditoria.ver` | Eventos (máx. 1000) + verificación de cadena | `control.py:68-76` |
| GET | `/api/auditoria/exportar` | `auditoria.exportar` | CSV o JSONL; registra la exportación | `control.py:79-87` |
| GET | `/api/seguridad` | `ver` | Lista de controles, CSP, cadena, libro, lector OCR, versiones | `control.py:90-128` |
| POST | `/api/demo/restablecer` | `demo.restablecer`; 404 si no es demo | Borra tablas de negocio y resiembra | `control.py:131-139` |
| GET | `/api/simulador/escenarios` | `ver` | Catálogo de 14 escenarios, rieles, periodos | `rutas/simulador.py:16` |
| GET | `/api/simulador/escenarios/{codigo}` | `simulador.usar` | Prepara un escenario | `simulador.py:25` |
| POST | `/api/simulador/factura` | `simulador.usar` | Crea factura sintética (60/min) | `simulador.py:33-42` |
| POST | `/api/simulador/anio` | `simulador.usar` | Simula 1-36 meses aislado (10/min) | `simulador.py:45-48` |
| GET | `/api/personas` | `usuarios.ver` | Personas, invitaciones, roles | `rutas/personas.py:21` |
| POST | `/api/personas/invitar` | `usuarios.gestionar` | Crea invitación; devuelve el código una sola vez | `personas.py:27` |
| DELETE | `/api/personas/invitaciones/{inv_id}` | `usuarios.gestionar` | Revoca invitación | `personas.py:38` |
| POST | `/api/personas/registro` | ninguno | Alta con código de invitación (8/15 min por IP, 6/15 min por correo) | `personas.py:46-57` |
| PUT | `/api/personas/{usuario_id}/rol` | `usuarios.gestionar` | Cambia rol | `personas.py:60` |
| PUT | `/api/personas/{usuario_id}/activo` | `usuarios.gestionar` | Activa/desactiva (cierra sesiones) | `personas.py:68` |
| POST | `/api/personas/{usuario_id}/desbloquear` | `usuarios.gestionar` | Quita bloqueo por intentos | `personas.py:76` |
| POST | `/api/personas/mi-contrasena` | sesión | Cambio de la propia contraseña | `personas.py:84` |
| GET | `/api/docs`, `/api/openapi.json` | solo modo demo | Documentación OpenAPI | `main.py:40-41` |
| GET | `/{ruta}` y `/assets/*` | ninguno | Sirve `web/dist` si existe; si no, no hay ruta | `main.py:74-82` |

Códigos de error de negocio: `ErrorNegocio` se responde 409 (`main.py:58-60`); validación Pydantic 422 (`main.py:63-66`); cuerpo > (10+2) MB 413 por cabecera `content-length` (`main.py:26,47`).

---

## 5. Base de datos

SQLAlchemy 2.0. SQLite por defecto en `VAR/kauta.db` (`config.py:76`), con `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL` (`db.py:19-26`). PostgreSQL por `KAUTA_BD`. Las tablas se crean con `Base.metadata.create_all` al arrancar (`servicios/semilla.py:141`); migraciones (Alembic): NO ENCONTRADO. Dinero `NUMERIC(18,2)`, tasa `NUMERIC(18,6)` (`modelos.py:24-25`).

| Tabla (clase) | Columnas clave | Restricciones / índices únicos | Evidencia |
|---|---|---|---|
| `organizaciones` | id, nombre, id_fiscal, datos(JSON) | PK id | `modelos.py:35` |
| `usuarios` | correo, nombre, cargo, rol, hash_contrasena, totp_cifrado, mfa_activo, totp_ultimo_paso, activo, intentos_fallidos, bloqueado_hasta | `correo` único + índice; CHECK `rol IN ('ceo','cfo','cto')` | `modelos.py:43-59` |
| `invitaciones` | correo, rol, hash_codigo, prefijo, expira_en, usada_en, revocada, intentos | CHECK rol; índice `ix_invitaciones_abiertas(correo, usada_en)` | `modelos.py:62-85` |
| `sesiones` | id (= SHA-256 del token), usuario_id (FK CASCADE), csrf, ultima_actividad, expira_en, ip, mfa_verificada_en, revocada | PK id | `modelos.py:88-100` |
| `beneficiarios` | id, nombre, id_fiscal, pais, estado, contrato(JSON), riel, moneda_recepcion, banco, cuenta_cifrada, cuenta_ultimos4, titular_registrado | CHECK `estado IN ('activo','bloqueado')`; índice id_fiscal | `modelos.py:106-129` |
| `cambios_cuenta` | beneficiario_id (FK), factura_id, cuenta_nueva_cifrada, ultimos4_nuevos, estado, solicitada_por, verificada_por, metodo_verificacion | CHECK estado en (pendiente, aprobado, rechazado) | `modelos.py:132-148` |
| `reglas_versiones` | version (PK), parametros(JSON), creada_por, motivo, cambios(JSON) | PK version | `modelos.py:151-158` |
| `facturas` | id (F01, S01, N001, SIM001, Y...), archivo, canal, origen, hash_documento, hashes(JSON), extraccion(JSON), metodo_lectura, modelo, beneficiario_*, numero, id_fiscal_unico, monto, moneda, monto_usd, periodo, decision, decision_inicial, estado, motivo, motivo_inicial, reglas, reglas_iniciales, version_reglas, aprobaciones_requeridas, excluir_firmante, resuelta_en | CHECK decision en (pagar, frenar, escalar); CHECK estado en (pagada, frenada, pendiente, rechazada, devuelta); índices en hash_documento, beneficiario_id, beneficiario_clave, id_fiscal_unico, periodo, estado | `modelos.py:164-206` |
| `aprobaciones` | factura_id, usuario_id, nivel, accion, comentario, correcciones, reglas_revisadas, datos_firmados, firma, con_mfa | UNIQUE `ux_una_aprobacion_por_persona(factura_id, usuario_id)`; CHECK accion en (aprobar, rechazar) | `modelos.py:209-227` |
| `eventos_costo` | factura_id (nulo para infraestructura), periodo, fuente, origen_id, importe_nano_usd (nulo = desconocido), tokens_*, latencia_ms, paginas, minutos, tarifa_version, simulado | UNIQUE `ux_costo_una_vez(fuente, origen_id)`; CHECK fuente en 8 valores | `modelos.py:233-262` |
| `wallet_cuentas` | codigo (PK), nombre, tipo, moneda | PK codigo | `modelos.py:268-274` |
| `wallet_asientos` | id, fecha, tipo, descripcion, referencia, periodo | índice referencia | `modelos.py:277-285` |
| `wallet_movimientos` | asiento_id, cuenta, debito, credito | CHECK `debito>=0 AND credito>=0 AND (debito=0 OR credito=0)` | `modelos.py:288-296` |
| `pagos` | id (PAG-000001), factura_id, riel, monto_usd, monto_destino, tasa_referencia, tasa_aplicada, comision_usd, costo_fx_usd, estado, clave_idempotencia, datos_firmados, firma, linea_tiempo | `clave_idempotencia` única; índice único parcial `ux_un_pago_vivo_por_factura(factura_id) WHERE estado != 'devuelto'`; CHECK estado en (reservado, enviado, liquidado, devuelto); CHECK `monto_usd > 0` | `modelos.py:299-332` |
| `auditoria` | id, ts, tipo, actor, entidad, entidad_id, resumen, datos(JSON), hash_anterior, hash | `hash` único; índices tipo, entidad_id | `modelos.py:338-349` |
| `idempotencia` | clave (PK), usuario_id, ruta, hash_solicitud, respuesta | PK clave | `modelos.py:352-359` |

Hechos sobre "solo inserción":
- Declarado en comentarios: "Las tablas de auditoría y del libro mayor solo reciben INSERT" (`modelos.py:9`).
- Lo que hace el código: `auditoria.registrar` solo inserta (`servicios/auditoria.py:33-47`); `wallet.asiento/transferir` solo insertan (`servicios/wallet.py:45-62`). La integridad se verifica por lectura: `auditoria.verificar` (`auditoria.py:50-61`) y `wallet.verificar_libro` (`wallet.py:75-85`).
- Disparadores (triggers), permisos de BD o reglas que impidan UPDATE/DELETE en esas tablas: NO ENCONTRADO.
- `semilla.restablecer` borra con `DELETE` las tablas de `TABLAS_NEGOCIO`, que incluyen `EventoAuditoria`, `Asiento`, `Movimiento` y `EventoCosto` (`semilla.py:149-158`); solo está disponible con modo demo (`control.py:133-134`).
- `eventos_costo` se agrega y no se sobrescribe: si llega la misma clave con otro importe se conserva el primero y se audita `costo.conflicto` (`servicios/costos.py:46-59`).
- Tabla `idempotencia` y su modelo `ClaveIdempotencia`: se borra en `restablecer` (`semilla.py:149`) pero ninguna ruta ni servicio la escribe ni la lee (búsqueda de `ClaveIdempotencia` en `servidor/`: solo `modelos.py:352` y `semilla.py`). La idempotencia que sí funciona está en `pagos.clave_idempotencia` (`pagos.py:159-162`).
- Hash/firma de datos: `facturas` no guarda firma propia; las firmas están en `aprobaciones.firma` y `pagos.firma` (HMAC).

---

## 6. Las 13 reglas (`kauta/motor.py`)

Catálogo: `motor.py:29-43`. Los valores salen de `data/reglas.json` (copiado a la tabla `reglas_versiones` como versión 1 al sembrar: `semilla.py:117-119`); el motor los lee del diccionario `reglas` que recibe (`motor.py:197-218`). Valores actuales de `data/reglas.json`:

| Clave | Valor | Línea |
|---|---|---|
| `version` | 1 | `reglas.json:2` |
| `periodo_actual` | "2026-10" | `reglas.json:5` |
| `tasas_cambio` | USD 1, COP 3200, MXN 18.4 | `reglas.json:6-11` |
| `monedas_permitidas` | USD, COP, MXN | `reglas.json:12-16` |
| `presupuesto_periodo_usd` | 15000 | `reglas.json:17` |
| `umbral_aprobacion_usd` | 3000 | `reglas.json:18` |
| `limite_maximo_pago_usd` | 10000 | `reglas.json:19` |
| `limite_beneficiario_periodo_usd` | 4000 | `reglas.json:20` |
| `tolerancia_contrato_pct` | 2 | `reglas.json:21` |
| `confianza_minima` | 0.85 | `reglas.json:22` |

| Id | Nombre | Efecto | Umbral / clave de `reglas.json` | Cómo se decide (falla si...) | Línea de evaluación |
|---|---|---|---|---|---|
| R01 | Datos legibles, completos y válidos | escalar (se vuelve **frenar** si el documento es nota crédito, recibo de pago u "otro": `motor.py:51-55,246-248`) | `confianza_minima` 0.85 | tipo no cobro; alguna validación `valido=False`; faltan beneficiario, número, moneda, monto o (si no es XML fiscal) vencimiento; tipo a revisar (nota débito, documento soporte, desconocido); confianza < mínimo en beneficiario, numero_factura, moneda o monto (`CAMPOS_CRITICOS:48`) | `motor.py:225-269` |
| R02 | Moneda permitida | escalar | `monedas_permitidas`, `tasas_cambio` | moneda fuera de la lista, o sin tasa; "no_aplica" si no hay moneda | `motor.py:271-278` |
| R03 | Factura no duplicada | frenar | ninguna | mismo `id_fiscal_unico` (CUFE/UUID/CAE), o intersección de hashes SHA-256, o mismo número del mismo beneficiario, contra todo el historial (sin importar estado) | `motor.py:280-297` |
| R04 | Un solo cobro por periodo (contrato fijo) | frenar | ninguna | contrato `fijo_mensual` y ya hay cobro del mismo beneficiario y periodo en estado `pagada` o `pendiente` (`ESTADOS_ACTIVOS:49`); no aplica a contrato por horas ni sin beneficiario | `motor.py:299-312` |
| R05 | Beneficiario no bloqueado | frenar | estado del beneficiario | beneficiario con `estado == "bloqueado"` | `motor.py:314-318` |
| R06 | Beneficiario en la lista permitida | escalar | lista de beneficiarios | no hay coincidencia por id fiscal (o por nombre sin id fiscal) con un beneficiario `activo`; si el nombre coincide pero el id fiscal no, falla | `motor.py:320-330`, búsqueda `:147-162` |
| R07 | Cuenta de pago igual a la registrada | escalar | `cuenta_registrada` (últimos 4) | últimos 4 dígitos de `cuenta_destino` distintos de los registrados; si la factura no trae cuenta, cumple | `motor.py:332-342` |
| R08 | Monto cuadra con lo acordado | escalar | `tolerancia_contrato_pct` 2 | `abs(diferencia %) > tolerancia` frente al contrato (fijo mensual, o horas x tarifa); sin horas en contrato por horas falla | `motor.py:344-369` |
| R09 | Dentro del límite máximo por pago | frenar | `limite_maximo_pago_usd` 10000 | `monto_usd > máximo` | `motor.py:371-379` |
| R10 | Dentro del umbral de aprobación humana | escalar | `umbral_aprobacion_usd` 3000 | `monto_usd > umbral` | `motor.py:381-388` |
| R11 | Dentro del límite por beneficiario en el periodo | escalar | `limite_beneficiario_periodo_usd` 4000 | pagado del beneficiario en el periodo (solo estado `pagada`) + esta factura > límite | `motor.py:390-404` |
| R12 | Saldo suficiente en el periodo | frenar | `presupuesto_periodo_usd` 15000 | `monto_usd > presupuesto - pagado_periodo` (suma de facturas `pagada` del periodo, `:214-218`) | `motor.py:406-413` |
| R13 | Sin instrucciones sospechosas | escalar | alerta `instruccion_sospechosa` (viene del extractor) | la extracción trae esa alerta | `motor.py:415-421`; detector en `extractor.py:38-42,160-162,306-307` |

Conversión a USD: `monto / tasa` con redondeo `ROUND_HALF_UP` a 2 decimales (`motor.py:138-144`).

Prioridad y agregación (`motor.py:423-451`):
- Se ordenan los resultados por id (`:424`).
- `PRIORIDAD_FRENAR = [R05, R03, R04, R09, R12]` (`:45`); `PRIORIDAD_ESCALAR = [R06, R13, R07, R01, R08, R10, R11, R02]` (`:46`).
- Si R01 falla con efecto frenar (documento que no es cobro) entra primero a `frenos` (`:428-429`). Si hay alerta `documento_rechazado`, R01 pasa al primer lugar de `escalas` (`:430-432`).
- Si hay algún freno: decisión `frenar`, motivo principal = primero de la lista, el resto se anexa como "Además" (`:433-437,450-451`). Si no, si hay escalada: `escalar` (`:438-442`). Si no, `pagar` (`:443-449`).
- Un error inesperado en `_evaluar` produce `escalar` con motivo de error, nunca `pagar` (`:188-194`).
- `revisar_reglas_duras` es un alias de `evaluar` (`:476-478`).
- Firmas requeridas se calculan fuera del motor: ver sección 8.

Reglas con 0 casos esperados como principal en `data/esperado.csv`: R02 y R13 (R13 solo aparece como motivo adicional de F08: `esperado.csv:9`).

---

## 7. Flujo de una factura, de la carga al pago

Entrada por la API (usuario con `facturas.cargar`, es decir CTO):

1. `POST /api/facturas/cargar` → `rutas/negocio.py:127`. Límite 30/min (`:128`), tope de tamaño (`:129-132`), nombre saneado (`:133`), validación por bytes mágicos (`_tipo_real:29-47`).
2. `agente.procesar_archivo` (`servicios/agente.py:131`): llama `EXTRACTOR.extraer` (`:133`), guarda el archivo con nombre = SHA-256 + extensión en `VAR/archivos` (`guardar_archivo:118-125`) y llama `registrar` (`:134`).
3. `ExtractorServidor.extraer` (`agente.py:62-69`) → `ExtractorReferencia.extraer` (`extractor.py:331-349`): `leer_documento` (`:135`) → `extraer_xml` (XML fiscal) → si el nombre del archivo está en `data/referencia_extracciones.json` usa esa extracción → si hay rechazos de seguridad, extracción rechazada → `extraer_ocr` → si nada, `ExtraccionNoDisponible`. Solo en ese caso y con `ANTHROPIC_API_KEY` se llama `ExtractorIA.extraer` (`agente.py:65-67`). Detalle en sección 11.
4. `_resultado` aplica `enriquecer` (`extractor.py:311-313,279-308`): valida id fiscal, contrasta identificadores (CUFE/UUID/CAE, QR), verifica receptor contra `EMPRESA`, anota rechazos de seguridad y añade alerta `instruccion_sospechosa`.
5. `agente.registrar` (`agente.py:137`), bajo candado `BLOQUEO` (`:140`):
   a. Lee reglas vigentes (`reglas_vigentes:78`), beneficiarios (`beneficiarios_motor:83`) y el historial (`historial:90`).
   b. `wallet.asegurar_fondeo` fondea la sub-wallet `cxp` del periodo si es el actual o el siguiente (`:147`, `wallet.py:93-99`, `periodos_abiertos:97-100`).
   c. `motor.evaluar` (`:151`) → `Decision`.
   d. `aprobaciones_requeridas` = 0 si no es escalar; 1 si escala; 2 si escala y `monto_usd > umbral` (`:154`).
   e. Inserta `Factura` con estado derivado: pagar → pagada, frenar → frenada, escalar → pendiente (`ESTADO:36`, `:156-165`).
   f. `costos.registrar_lectura` (`:168`) y `auditoria.registrar("factura.decision")` (`:169-173`).
   g. Si la decisión es `pagar`: `_pagar_o_escalar` (`:174-175`, `:184-199`).
   h. Si R07 falló y hay cuenta destino: crea `CambioCuenta` pendiente (`_solicitar_cambio_cuenta:176-178,202-219`).
   i. `commit` (`:179-180`).
6. `pagos.crear_y_ejecutar` (`servicios/pagos.py:141-220`), dentro de `bd.begin_nested()` (`agente.py:188`): beneficiario activo (`:144`) → re-verifica firmas de aprobaciones (`:146`) → riel válido (`:149-151`) → confirmación de titular (`:152-154`) → saldo real de `cxp` (`:155-158`) → clave de idempotencia (`:159-162`) → `cotizar` (`:164`) → inserta `Pago` (`:182-188`) → `costos.registrar_pago` (`:190`) → asientos: reserva cxp→reservas, envío reservas→tránsito, comisión y costo FX desde `operativa` (`:192-197`) → liquidación tránsito→proveedores o devolución (`:199-214`) → auditoría `pago.creado` (`:216`). Si lanza `ValueError`, la factura pasa a `escalar/pendiente` con motivo "Control del pago" (`agente.py:190-198`).
7. Si la decisión fue `escalar` (factura pendiente):
   - `GET /api/aprobaciones` la muestra con preguntas por regla blanda fallida (`negocio.py:180`, `vistas.preguntas:41-61`).
   - `POST /api/facturas/{fid}/aprobar` → `agente.aprobar` (`agente.py:225`): estado pendiente (`:231`); quien cargó no firma (`:233`); no se firma dos veces (`:236`); `excluir_firmante` (`:238`); comentario obligatorio (`:241`); aplica correcciones y las deja con confianza 1.0 (`:246-254`); exige vencimiento si no es XML fiscal (`:255`); **re-evalúa el motor y bloquea si falla una regla dura** (`:257-264`); guarda `Aprobacion` firmada con HMAC (`:272-278`); `costos.registrar_revision` (`:279`); si faltan firmas devuelve "falta otra persona" (`:283-286`); si completa, `estado = pagada` y `_pagar_o_escalar` (`:288-298`).
   - `POST .../rechazar` → `agente.rechazar` (`:303`): estado `rechazada` con firma (`:310-319`).
8. Reevaluación: `agente.reevaluar` (`:324-363`) se llama tras `PUT /api/reglas` (`negocio.py:270`) y tras aprobar un cambio de cuenta (`negocio.py:232`). Solo toca facturas `frenada` o `pendiente`; cuando la dispara una persona nunca paga sola (`:347-353`).
9. Fallos: un pago devuelto deja la factura `devuelta` (`pagos.py:199-208`); `POST /api/pagos/{pid}/reintentar` reevalúa y crea un nuevo pago con `intento+1` (`dinero.py:66-87`).

Entrada alternativa del set: al arrancar, `semilla.iniciar` procesa los 20 archivos de `data/facturas` con `agente.procesar_archivo(... "set", "Agente Kauta", "buzon@brisamar.example")` (`semilla.py:129-137`, llamado desde `main.py:31-32`). Entrada del simulador: `simulador.crear_factura` llama `agente.registrar` con método `simulador` (`simulador.py:236-250`).

---

## 8. Roles, permisos y firmas

Definidos en `servidor/seguridad/permisos.py:10-22` y aplicados en el servidor con `requiere(permiso)` (`sesiones.py:90-96`), que responde 403 si el rol no lo tiene. La pantalla solo oculta botones con `puede()` (`web/src/api.ts:264`).

| Permiso | CFO | CEO | CTO |
|---|---|---|---|
| `ver` (implícito para cualquier rol con permisos) | sí | sí | sí |
| `facturas.aprobar` (aprobar/rechazar) | sí | sí | no |
| `facturas.cargar` | no | no | sí |
| `reglas.editar` | sí | no | no |
| `cuentas.verificar` | sí | no | no |
| `cuentas.solicitar` | no | no | sí (ninguna ruta lo exige: NO ENCONTRADO su uso) |
| `wallet.fondear` | sí | no | no |
| `pagos.reintentar` | sí | no | no |
| `simulador.usar` | sí | sí | sí |
| `auditoria.ver` / `auditoria.exportar` | sí | sí | sí |
| `usuarios.ver` / `usuarios.gestionar` | no | no | sí |
| `demo.restablecer` | no | no | sí |

Personas de demo (`semilla.py:29-33`): Carlos Rivera, CFO, `carlos.rivera@brisamar.example`; Mariana Torres, CEO, `mariana.torres@brisamar.example`; Tomás Herrera, CTO, `tomas.herrera@brisamar.example`. Contraseña de demo en el código: `semilla.py:28` (se expone también por `GET /api/auth/demo`, `auth.py:119`).

Firmas requeridas por factura (`servicios/agente.py:154`, recalculado en `:346`):
- **0 firmas**: la decisión del motor fue `pagar` (paga el agente, sin persona). Los controles del pago aún pueden devolverla a escalar (`:184-199`).
- **1 firma**: decisión `escalar` y `monto_usd <= umbral_aprobacion_usd` (3000).
- **2 firmas**: decisión `escalar` y `monto_usd > umbral`. Deben ser personas distintas (UNIQUE en `aprobaciones`: `modelos.py:226`; chequeo `agente.py:236-237`). Como solo CFO y CEO tienen `facturas.aprobar`, con los 3 usuarios de demo las dos firmas son CFO y CEO.
- Una factura `frenar` no tiene ruta de aprobación (`agente.py:231` exige estado `pendiente`).
- Reglas duras no se saltan con firmas: se re-evalúan al aprobar (`agente.py:257-264`).

Segregación aplicada en servidor:
- Quien cargó la factura no la aprueba: `f.cargada_por == u.correo` (`agente.py:233-234`). Las del set llevan `cargada_por="buzon@brisamar.example"` (`semilla.py:133`), por lo que nadie queda excluido.
- Quien pidió un cambio de cuenta no lo verifica (`negocio.py:214-215`).
- Quien provocó una reevaluación (cambió reglas o cuenta) no puede ser la firma única (`agente.py:238-240,347-353`).
- Se mantiene al menos un usuario activo con el rol administrador `cto` (`usuarios.py:154-155,170-171`).
- Aprobar con TOTP activo exige el código (`negocio.py:158-162`); en producción, sin TOTP activo la aprobación se rechaza (403) (`negocio.py:163-164`).

---

## 9. Seguridad

| Tema | Qué hace el código | Evidencia |
|---|---|---|
| Sesión | Token aleatorio 256 bits (`secrets.token_urlsafe(32)`); en BD solo su SHA-256; inactividad 30 min, duración máxima 8 h; sesión nueva en cada ingreso | `sesiones.py:30-46`, `config.py:55-56` |
| Cookie | `HttpOnly`, `SameSite=Strict`, `Path=/`, `Secure` y nombre `__Host-kauta_sesion` solo si `KAUTA_ORIGEN` empieza por `https://` | `sesiones.py:44-45`, `config.py:52,65-67,81` |
| CSRF | Token por sesión en cabecera `X-CSRF-Token` para métodos no seguros (`hmac.compare_digest`) | `sesiones.py:78-80` |
| Origin | Para métodos no GET/HEAD/OPTIONS, si llega cabecera `Origin` debe estar en `{KAUTA_ORIGEN} + KAUTA_ORIGENES_ADICIONALES (+ localhost 5173/8000 en demo)`; sin cabecera Origin pasa | `cabeceras.py:21,26-30` |
| CORS | NO ENCONTRADO (no hay middleware CORS; el modelo es mismo origen o proxy de Vercel) | búsqueda en `servidor/` |
| Cabeceras | CSP estricta (`default-src 'self'`, sin scripts en línea), nosniff, `X-Frame-Options DENY`, `Referrer-Policy no-referrer`, `Permissions-Policy`, COOP/CORP same-origin, `X-Request-ID`, HSTS si HTTPS, `Cache-Control: no-store` en `/api/` | `cabeceras.py:19-20,33-45` |
| Límite de cuerpo | `content-length` > 12 MB → 413 | `main.py:26,44-49` |
| Contraseñas | Argon2id (64 MiB, 3 iteraciones, 4 hilos), mínimo 15 caracteres, lista de 12 comunes, hash señuelo contra enumeración | `contrasenas.py:14-22,40-48` |
| Bloqueo | 5 intentos fallidos → bloqueo 15 min (`MAX_INTENTOS`, `BLOQUEO_MIN`) | `auth.py:23-24,45-52` |
| Límites de tasa (en memoria, por proceso) | login 10/min por IP y 8/15 min por cuenta; persona 120/min por IP; registro 8/15 min IP y 6/15 min correo; carga 30/min usuario; simulador 60/min y año 10/min | `auth.py:36-37,98`, `personas.py:50-51`, `negocio.py:128`, `simulador.py:35,47`; `limites.py:14-41` |
| TOTP | RFC 6238, ventana ±30 s, un código se usa una sola vez; secreto cifrado | `totp.py:32-45` |
| Cifrado en reposo | AES-256-GCM, nonce 96 bits, AAD ligada al registro (`cuenta:{id}`, `totp:{id}`, `cambio:{id}`); formato `v1:<id clave>:<base64>`; cubre cuentas bancarias, secretos TOTP, cuentas nuevas | `cifrado.py:25-36`, `semilla.py:114`, `totp.py:29` |
| Firmas | HMAC-SHA256 sobre JSON canónico de los datos exactos de cada aprobación y de cada orden de pago; se re-verifican antes de pagar | `firma.py:18-27`, `pagos.py:118-133,146-148` |
| Auditoría | Cadena HMAC-SHA256 (clave `KAUTA_CLAVE_AUDITORIA`) encadenando `hash_anterior`; verificación al leer | `auditoria.py:29-61` |
| Claves | Tres claves (datos, firma, auditoría) de >= 32 bytes por variable de entorno; en demo se generan y se guardan en `VAR/<nombre>.key` modo 600; en producción faltar una impide arrancar | `config.py:27-41` |
| Detección de instrucciones en documentos | 10 patrones regex en español/inglés sobre el texto del documento y de los XML; marca alerta → R13 escala. El prompt de IA también le dice al modelo que trate el documento como dato | `extractor.py:38-42,160-162,306-307,44-50` |
| XML | `defusedxml` con `forbid_dtd/entities/external`; máximo 5 MB | `lectores_xml.py:39,98-107` |
| ZIP | Máx. 25 MB, 20 archivos, 60 MB descomprimido, ratio 200; rechaza rutas peligrosas, ZIP con contraseña, ZIP anidado | `lectores_xml.py:40-43,372-407`, `extractor.py:124-126` |
| Archivos subidos | Extensiones permitidas, validación por bytes mágicos, UTF-8 en texto; guardados con nombre = SHA-256; vista previa re-codificada a PNG | `negocio.py:25-47,116`, `agente.py:118-125` |
| Pagos | Confirmación de titular (nombre del titular registrado = nombre del beneficiario), re-verificación de firmas, saldo real de `cxp`, clave de idempotencia y un solo pago vivo por factura (índice parcial) | `pagos.py:112-115,146-162`, `modelos.py:330-331` |
| Cambio de cuenta | Nunca se aplica solo; requiere verificación por otra persona con método registrado | `negocio.py:208-233` |
| Docker | usuario no root, FS de solo lectura, `cap_drop ALL`, `no-new-privileges` | `Dockerfile:13,25`, `docker-compose.yml:11-15` |
| systemd | `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `UMask=0077` | `ops/kauta.service:14-18` |
| Front | Sin `innerHTML` ni `dangerouslySetInnerHTML` en `web/src` (búsqueda sin resultados) | búsqueda en `web/src` |

**Qué NO existe (verificado por lectura/búsqueda):**
- Autenticación real en la pantalla: el front no tiene formulario de login; solo llama `POST /api/auth/persona` (`web/src/api.ts:156-161`, `App.tsx:38-42`), que devuelve 404 en modo producción (`auth.py:95-96`). La pantalla `Login.tsx` y `Personas.tsx` se eliminaron en el commit `7a9e108`.
- Pantalla de activación de TOTP: los endpoints existen (`auth.py:124-162`), la pantalla no los llama (búsqueda de `mfa/` en `web/src`: NO ENCONTRADO; solo hay un campo de código en `Detalle.tsx:190-193` si el usuario ya tiene `mfa_activo`).
- Passkeys/WebAuthn: NO ENCONTRADO (mencionado como hoja de ruta en `totp.py:7`).
- Límite de tasa compartido entre procesos (Redis/gateway): NO ENCONTRADO; el limitador y el candado `BLOQUEO` son locales al proceso (`limites.py:2-3`, `servicios/__init__.py:4-6`). La documentación exige un solo proceso (`README.md:92`).
- Rotación de claves: NO ENCONTRADO (el descifrado falla si cambia el id de clave: `cifrado.py:33-34`).
- KMS/HSM: NO ENCONTRADO (solo se menciona en comentarios: `cifrado.py:8-9`).
- Reintento seguro de la clave de idempotencia por cabecera HTTP (`Idempotency-Key`): NO ENCONTRADO.
- Lista de revocación de IP / geobloqueo / WAF: NO ENCONTRADO.

---

## 10. Costos y FinOps

**Tarifas** (`data/tarifas.json`, versión 1; "simuladas y declaradas, no son precios de ningún proveedor": línea 3):

| Concepto | Valor | Línea |
|---|---|---|
| IA entrada / caché / salida | 3.0 / 0.3 / 15.0 USD por millón de tokens | `tarifas.json:4` |
| IA tokens por página | 6000 entrada, 600 salida; latencia 3500 ms | `tarifas.json:4-5` |
| OCR | 0.0005 USD por página; 1800 ms | `tarifas.json:6` |
| XML | 0.0 USD; 40 ms | `tarifas.json:7` |
| Texto | 0.0 USD; 120 ms | `tarifas.json:8` |
| Revisión humana | 40.0 USD/hora; 3 min por respuesta; 1 min por firma | `tarifas.json:9` |
| Infraestructura | 30.0 USD por mes | `tarifas.json:10` |

La tarifa `usd_por_millon_cache` (0.3) y el campo `tokens_cache` (siempre 0) no se usan en ningún cálculo (`costos.py:112`).

**Libro de costos** (`eventos_costo`, `modelos.py:233-262`): importe en "nano USD" (1e-9) entero; NULL = desconocido, nunca cero; clave única (fuente, origen_id); se escribe en la misma transacción que la acción (`costos.py:9-12`). Fuentes: `lectura_xml`, `lectura_texto`, `lectura_ocr`, `lectura_ia`, `revision_humana`, `pago_comision`, `pago_cambio`, `infraestructura` (`modelos.py:233-234`).

Cómo se escribe cada evento:
- Lectura (`costos.py:73-115`): el camino se decide **por extensión de archivo y confianza guardada, no por el lector que realmente se usó**: `.xml`/`.zip` o `metodo_lectura == "xml_fiscal"` → `lectura_xml`; imágenes (`.jpg .jpeg .png .webp .tif .tiff`) → `lectura_ocr`, y además `lectura_ia` si alguna de beneficiario/numero_factura/moneda/monto tiene confianza < `confianza_minima`; todo lo demás (PDF, .eml, .txt, simulador) → `lectura_texto`. El costo de IA = (6000×3.0 + 600×15.0)/1e6 = 0.027 USD por página, con 1 página fija (`costos.py:90,107-111`).
- Revisión humana (`costos.py:118-125`): 40 × minutos / 60; minutos = 1 si es aprobación de nivel > 1, si no 3. Cada `Aprobacion` genera un evento (`origen_id = aprobacion:{id}`).
- Pago (`costos.py:128-133`): `pago_comision` = comisión del riel; `pago_cambio` = costo FX si el destino no es USD.
- Infraestructura (`costos.py:67-70`): un evento por mes, sin factura, 30 USD.

**Métricas expuestas** (`servicios/metricas.py`):

| Métrica | Cálculo | Evidencia |
|---|---|---|
| `autonomia_pct` | facturas con `decision_inicial` en (pagar, frenar) / total | `metricas.py:56,79` |
| `autonomia_set_pct` | igual, restringida a las facturas cuyo id está en `esperado.csv` | `:70,74,83` |
| `set_aciertos / set_total` | coincide `decision_inicial` y regla principal del `motivo_inicial` con `esperado.csv` | `:71-72,82` |
| `pagos_fuera_de_reglas` | pagadas sin aprobación con alguna falla; o aprobadas con falla de regla dura; o con menos firmas que las requeridas | `:57-68` |
| `explicadas_pct` | facturas con motivo y reglas / total | `:81` |
| `trampas_detenidas / trampas_total` | del set, `tipo_caso == "trampa"`; detenida = `decision_inicial != "pagar"` | `:75,84` |
| `dinero_protegido_usd` | suma `monto_usd` de facturas frenadas y rechazadas | `:73` |
| `costo_por_factura_resuelta` | (costos de facturas finales + su parte de infraestructura) / número de finales | `:207-215` |
| `costo_de_pagar` | (comisión + cambio de facturas pagadas) / pagadas | `:217-223` |
| `leido_sin_ia` | facturas con evento de lectura y sin `lectura_ia` / facturas con lectura | `:225-230` |
| `cobertura` | casillas con importe conocido / casillas esperadas (lectura por factura, comisión y cambio por pago, revisión por aprobación, infraestructura por mes), tope 100 | `:232-256` |
| Infraestructura por factura | importe del mes / número de facturas finales del mes; se excluye una factura resuelta después del cierre del mes (hora Bogotá, UTC-5) | `:93-112,156-169` |
| Estados finales | `pagada`, `frenada`, `rechazada` | `modelos.py:363` |

`/api/resumen` (`control.py:28-58`): `metricas` = `metricas.base`; `lente` según rol (`metricas.py:338-368`): CFO = pagado, esperando firma, costo, dinero protegido; CEO = autonomía, pagos indebidos, dinero protegido + frase; CTO = costo, leído sin IA, cobertura. Además `serie` (acumulado pagado del periodo actual), `fallas_por_regla`, `pagos_por_riel`, `ultimas` (8), `extractor` (modo), `criterios` (autonomía, seguridad, explicabilidad: textos construidos con las métricas).

`/api/rendimiento` (`control.py:61-65`, `metricas.py:296-317`): 4 tarjetas (costo por resuelta, costo de pagar, leído sin IA, cobertura), `fuentes_usd` por grupo (lectura, revisión, pago, infraestructura), desglose de lectura (xml/texto/ocr/ia), `en_curso_usd` (costos de abiertas, sin infraestructura), `abiertas`, `numerador_usd`, `denominador`. Toda respuesta lleva `simulado: true`.

Recibo `/api/facturas/{fid}/recibo` (`metricas.py:259-289`): líneas lectura, revisión humana, comisión, cambio, infraestructura; `total_completo` falso si alguna línea es desconocida; "protegido" para frenadas/rechazadas o pagadas tras revisar R07.

Rieles (comisión fija USD y spread FX) en `pagos.py:37-71`: ACH 0.50, WIRE 15.00, SWIFT 25.00, SPEI 0.30 (spread 0.004), BREB 0.00 (0.005), ACH_CO 0.40 (0.005), PIX 0.00 (0.005), USDC 0.05. El costo cambiario es `monto_destino / tasa_aplicada - monto_usd` (`pagos.py:94-109`). Tasas de referencia salen de `tasas_cambio` de las reglas (`pagos.py:97`).

---

## 11. Extracción

Resolución de lector por factura (`servicios/agente.py:62-69` y `kauta/extractor.py:331-349`):

| Orden | Lector | Condición | `metodo_lectura` |
|---|---|---|---|
| 1 | XML fiscal exacto, sin IA | el documento trae un XML (o ZIP con XML) válido: CFDI 4.0, factura/nota crédito/nota débito UBL DIAN, contenedor DIAN | `xml_fiscal` (`extractor.py:220-232`) |
| 2 | Extracción de referencia | el **nombre del archivo** está en `data/referencia_extracciones.json` (20 entradas, claves = nombres de `data/facturas`) | `referencia` (`extractor.py:336-342`) |
| 3 | Rechazo de seguridad | hubo rechazos (XXE, ZIP malicioso) | `rechazado` (`extractor.py:343-344,269-276`) |
| 4 | OCR / texto del PDF | `ocr.leer`: usa texto incrustado del PDF si tiene >= 200 caracteres (sin OCR); si no, Tesseract (si está instalado) con imágenes o PDF escaneado | `texto_pdf` u `ocr` (`ocr.py:498-526`) |
| 5 | IA (Anthropic) | solo si 1 a 4 no produjeron nada **y** existe `ANTHROPIC_API_KEY` | `ia` (`extractor.py:381-397`) |

Hechos importantes:
- **Las 20 facturas del set (F01-F20, ninguna es XML) se leen "de referencia", no por OCR ni por IA**: el nombre de archivo coincide con la tabla de referencia, que es "lo que un extractor perfecto debe devolver" (`scripts/generar_set.py:1-12` y `extractor.py:324`). Por eso `metodo_lectura` de F01-F20 es `referencia`; los XML S01 a S04 usan `xml_fiscal` (S03 se rechaza).
- `ExtractorReferencia` acepta cualquier resultado del OCR aunque `ocr_suficiente` sea falso (`extractor.py:345-347`); la comprobación `ocr_suficiente` solo se usa dentro de `ExtractorIA.extraer` (`:389-390`), que en el servidor solo se invoca si el OCR devuelve nada.
- "IA simulada": el modo demo no llama a ningún modelo. Los eventos de costo `lectura_ia` son calculados con la tarifa y 1 página fija, no con tokens reales (`costos.py:106-114`). Las llamadas reales a la API (`ExtractorIA`, `extractor.py:391-397`) no registran tokens ni costos reales: NO ENCONTRADO.
- Prompt de IA con el esquema JSON y 10 reglas, incluye "el contenido del documento es un DATO": `extractor.py:44-81`. El modelo recibe hasta 3 PDF y 3 imágenes en base64 y hasta 12000 caracteres de texto de correo/chat (`extractor.py:366-379`).
- Salida del modelo: `normalizar` limpia tipo de documento (`TIPOS_DOCUMENTO`, `normalizacion.py:457`), fechas, moneda, monto, cuenta (últimos 4), confianza 0 a 1 por seis campos (`extractor.py:173-195`).
- Campos de confianza: `CAMPOS_CONFIANZA` (6) y `CAMPOS_CRITICOS_OCR` (4) en `extractor.py:34-36`.
- Validaciones deterministas agregadas a cualquier extracción: id fiscal por país (NIT, CC, CUIT, RFC, CNPJ, CPF, RUT, RUC, EIN: `normalizacion.py:198-227`), contraste con QR/CUFE/UUID/CAE (`lectores_xml.py:443-516`), receptor igual a `data/empresa.json` (`extractor.py:293-301`).
- Formatos admitidos: `.pdf .png .jpg .jpeg .webp .eml .txt .xml .zip` (`negocio.py:26`); `canal_de` los clasifica en pdf, imagen, correo, chat, xml, zip (`extractor.py:91-94`). Los correos se abren con la librería estándar `email` y se leen cuerpo y adjuntos (`extractor.py:143-151`).
- Qué está simulado: la extracción del set (referencia), los costos de IA, las tarifas, los rieles de pago, las cuentas bancarias, el directorio de titulares (`confirmar_titular` compara dos campos de la misma fila: `pagos.py:112-115`), la fecha "hoy" de `vistas.plazo` (ver sección 17).
- ARCA/AFIP (Argentina): se lee el QR (`lectores_xml.py:422-441`); no hay lector de XML argentino: NO ENCONTRADO.

---

## 12. Interfaz (`web/src`)

Una sola página (SPA) con ruteo por hash `#/ruta` (`api.ts:227-240`). No hay pantalla de login ni de personas (ver sección 9). Entrada: `index.html:14` → `main.tsx` → `App.tsx`. Al abrir: `GET /auth/yo`; si 401, `POST /auth/persona` con la última persona guardada en `localStorage` (`kauta:persona`, por defecto Carlos Rivera) (`App.tsx:36-43`, `api.ts:143-145`). Un 401 durante el uso reintenta una vez una lectura y pide repetir una escritura (`api.ts:178-185`).

| Ruta hash | Archivo (líneas) | Endpoints que consume | Evidencia |
|---|---|---|---|
| `#/resumen` (por defecto) | `pages/Resumen.tsx` (39) | GET `/resumen` | `Resumen.tsx:7` |
| `#/facturas` | `pages/Facturas.tsx` (145) | GET `/facturas`; POST `/facturas/cargar` (formulario); POST `/facturas/sorpresa` | `Facturas.tsx:16,37,49` |
| `#/facturas/{id}` | `pages/Detalle.tsx` (300) + `ReciboFactura.tsx` (18) | GET `/facturas/{id}`; POST `/facturas/{id}/aprobar` y `/rechazar`; GET `/facturas/{id}/recibo`; enlace `/api/pagos/{id}/comprobante` | `Detalle.tsx:17,138,280`, `ReciboFactura.tsx:7` |
| `#/pregunta` | `pages/Pregunta.tsx` (66) | GET `/aprobaciones` | `Pregunta.tsx:9` |
| `#/simulador` | `pages/Simulador.tsx` (345) | GET `/simulador/escenarios`, `/simulador/escenarios/{codigo}`; POST `/simulador/factura`, `/simulador/anio`, `/demo/restablecer` | `Simulador.tsx:58,74,99,268,26` |
| `#/wallet` | `pages/Wallet.tsx` (160) | GET `/wallet`, `/pagos`, `/rieles`; POST `/wallet/fondear`, `/pagos/{id}/reintentar` | `Wallet.tsx:15-17,29,38` |
| `#/rendimiento` | `pages/Rendimiento.tsx` (29) | GET `/rendimiento` | `Rendimiento.tsx:9` |
| `#/proveedores` | `pages/Proveedores.tsx` (126) | GET `/proveedores`, `/cambios-cuenta`; POST `/cambios-cuenta/{id}/verificar` | `Proveedores.tsx:9-10,101` |
| `#/reglas` | `pages/Reglas.tsx` (131) | GET `/reglas`; POST `/reglas/simular`; PUT `/reglas` | `Reglas.tsx:17,37,43` |
| `#/auditoria` | `pages/Auditoria.tsx` (59) | GET `/auditoria?limite=300`; enlaces a `/api/auditoria/exportar?formato=csv` y `jsonl` | `Auditoria.tsx:13,24-25` |
| `#/seguridad` | `pages/Seguridad.tsx` (15) | GET `/seguridad` | `Seguridad.tsx:6` |

Marco (`App.tsx:56-119`): barra lateral con grupos Operar / Dinero / Control (`NAV:17-28`), navegación móvil de 5 + "Más", contador de pendientes desde GET `/aprobaciones` y periodo desde GET `/reglas` (`:62-65`), selector de persona ("CambiarPersona", `:121-139`) que llama GET `/auth/demo` y POST `/auth/persona`.

Componentes compartidos (`ui.tsx`): `Logo`, `EstadoChip`, `Sello`, `TiraReglas`, `Panel`, `Encabezado`, `Boton`, `Campo`, `Aviso`, `Vacio`, `Cargando`, `EstadoCarga`, `TarjetasMetricas`, `ProveedorToast`/`useToast`, `Modal`, `Hash`, `Dato`, `BarraPresupuesto`, `LineaTiempo`, `GraficoSaldo`, `Validaciones` (líneas 6-346). Cliente HTTP, hooks `useApi`, `useRuta`, `useCambios`, formateo de dinero/fechas en `api.ts`.

Permisos en la UI (solo ocultan controles): `puede()` en `Facturas.tsx:61,68`, `Auditoria.tsx:16,23`, `Proveedores.tsx:31`, `Reglas.tsx:29`, `Wallet.tsx:49,100`, `Detalle.tsx:131`, `Simulador.tsx:37,51`. El campo de código TOTP aparece solo si `usuario.mfa_activo` (`Detalle.tsx:190`).

Atributos `data-testid`: una sola aparición (`ui.tsx:187`, `data-testid="metricas"`).

---

## 13. Pruebas

Conteo leyendo `def test_` (no se ejecutó pytest). 60 funciones; con los 2 `parametrize` (13 y 5 casos: `test_formatos.py:22-27,52-55`) son 76 casos, que coincide con "76 pruebas" de `../docs/designs/kauta-estado-2026-10-17.md:9`.

| Archivo | Funciones | Qué cubre |
|---|---|---|
| `tests/test_kauta.py` | 9 | El set de 20 coincide con `esperado.csv` (`:35`); 13 reglas y explicación (`:49`); inyección no cambia la decisión (`:56`); aprobar no rompe reglas duras (`:64`); cambio de reglas reevalúa (`:74`); registro encadenado detecta alteración (`:83`); montos LatAm/EE. UU. (`:91`); error inesperado escala (`:99`); estrés con 0 pagos fuera de reglas (`:151`). Usa el agente en memoria `kauta/agente.py` |
| `tests/test_formatos.py` | 17 (33 casos) | Identificaciones (13 casos), CNPJ alfanumérico, validadores bancarios, montos (5), fechas por país, monedas, CFDI exacto, contenedor DIAN ZIP, XXE, zip slip y bomba, totales que no cuadran, QR ARCA, XML luego PDF duplicado, archivo malicioso, ids desde PDF, nota crédito nunca se paga, normalización de tipo de IA |
| `tests/test_servidor.py` | 28 | Base temporal (`:26`); set 20 de 20 por API (`:44`); sin sesión/CSRF (`:50`); contraseña incorrecta genérica (`:60`); permisos por rol (`:67`); regla dura no se salta (`:73`); doble aprobación y firmas (`:79`); firma alterada bloquea (`:95`); un solo pago vivo (`:111`); auditoría detecta alteración (`:124`); libro cuadrado (`:139`); simulador de año (`:145`); carga rechaza tipos falsos (`:152`); XML malicioso (`:161`); política de contraseñas (`:170`); invitación/registro/roles (`:180`); lector local sin IA (`:225`); persona sin contraseña (`:252`); persona mantiene permisos y CSRF (`:262`); cambio de reglas no paga solo (`:281`); quien cambia reglas no es firma única (`:292`); costos idempotentes (`:311`); costos no se confirman aparte (`:330`); invariante y tesis de IA (`:347`); restablecer determinista (`:372`); recorrido F12 y segunda firma (`:384`); orígenes públicos (`:418`); fallo tras crear pago revierte todo (`:430`) |
| `tests/test_costos.py` | 6 | Aceptación de costo por resuelta y de pagar, sin la pendiente, invariante recibos = numerador, cobertura, costo desconocido no es cero, mes cerrado no cambia recibos |
| `tests/conftest.py` | 0 (fixture) | Fija `KAUTA_VAR` y `KAUTA_BD` temporales antes de importar el servidor (`:11-13`) y limpia al final (`:16-22`) |

Pruebas de front (Jest/Vitest/Testing Library): NO ENCONTRADO. Pruebas de extremo a extremo: `scripts/probar_web.mjs` (Playwright, 157 líneas) invocable con `npm run test:e2e` o `python scripts/probar_web.py` (`web/package.json:11`, `scripts/probar_web.py:1-12`); según `README.md:111-115` recorre 390/1440 px, menú, firmas, recibos, carga XML, permisos, 401 y 502. No se ejecutó.

Scripts de verificación y medición (`scripts/`):
- `correr_set.py`: corre el set en modo demo o IA (`--modo ia`) y muestra decisiones; registro en `salidas/registro.jsonl` (`:1-8`).
- `medir_extraccion.py`: compara extracción (IA o demo) con `referencia_extracciones.json` (`:1-9`).
- `medir_ocr.py`: mide el lector local contra las extracciones verificadas (`:1-3`).
- `contrastar_validadores.py`: compara los validadores propios con `python-stdnum` y `clabe` sobre 55.000 casos (`:1-2`).
- `generar_set.py`: genera `data/*` desde una sola fuente (`:1-12`).
- `capturas_web.py` (Playwright Python) y `probar_web.mjs`: capturas y recorrido.
- `empaquetar.py`: arma `kauta-kit-v2.zip` (`:1-8`).

Otras verificaciones en código: `simulador.verificador_independiente` revisa pagos del simulador sin usar el motor (`servicios/simulador.py:260-301`); el script de la política de integración continua: NO ENCONTRADO.

---

## 14. Despliegue y operación

| Tema | Hecho | Evidencia |
|---|---|---|
| Arranque local | `uvicorn servidor.main:app --host 127.0.0.1 --port 8000 --workers 1` tras `npm ci`, `npm run typecheck`, `npm run build` | `README.md:22-33` |
| Dev front | `vite` en 5173 con proxy a 8000 | `web/vite.config.ts:9` |
| Streamlit (plan B) | `streamlit run app.py` | `app.py:4` |
| Docker | `EXPOSE 8000`, `HEALTHCHECK` a `/api/salud`, `KAUTA_VAR=/var/kauta` | `Dockerfile:12,26-27` |
| Servicio systemd | `ExecStart=.../python -m uvicorn servidor.main:app --host 127.0.0.1 --port 8840 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1`; carga `EnvironmentFile=/root/.config/kauta/runtime.env`; `ReadWritePaths=/root/.local/share/kauta/var`; `WorkingDirectory=/root/hackaton30xBlinka/kauta` | `ops/kauta.service:8-18` |
| Nginx | 80 redirige a 443 y atiende el reto ACME; 443 con Let's Encrypt a `proxy_pass http://127.0.0.1:8840`; `client_max_body_size 12m`; `proxy_read_timeout 120s`; host `kauta.2-25-233-186.sslip.io` | `ops/nginx.kauta:1-27` |
| Frontend en producción (documentado) | Vercel sirve React y reenvía `/api/*` por HTTPS al servidor | `README.md:64-97`, `web/vercel.json:6-10` |
| Contenido de `runtime.env` | NO ENCONTRADO (fuera del repositorio) | `ops/kauta.service:9` |

Variables de entorno (solo nombres):

| Variable | Uso | Evidencia |
|---|---|---|
| `KAUTA_MODO` | `demo` (por defecto) o `produccion` | `config.py:71`, `.env.example:2` |
| `KAUTA_BD` | URL de la base | `config.py:76`, `docker-compose.yml:8` |
| `KAUTA_VAR` | carpeta de datos/claves/archivos | `config.py:24`, `Dockerfile:12` |
| `KAUTA_CLAVE_DATOS`, `KAUTA_CLAVE_FIRMA`, `KAUTA_CLAVE_AUDITORIA` | claves base64 de >= 32 bytes | `config.py:77-79` |
| `KAUTA_ORIGEN` | origen público (por defecto `http://localhost:8000`); define cookie Secure | `config.py:73,81` |
| `KAUTA_ORIGENES_ADICIONALES` | lista separada por comas de orígenes autorizados (p. ej. Vercel) | `config.py:82` |
| `KAUTA_PREPARAR_RECORRIDO` | `1` para presupuesto USD 20.000 y primera firma de F10 al arrancar (solo demo) | `config.py:83`, `main.py:33-34` |
| `KAUTA_MODELO` | modelo de la API de Anthropic | `extractor.py:33` |
| `ANTHROPIC_API_KEY` | activa la lectura con IA | `agente.py:51` |
| `POSTGRES_PASSWORD` | contraseña de Postgres en compose | `docker-compose.yml:8,21`, `.env.example:11` |
| `KAUTA_URL`, `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | recorrido Playwright | `scripts/probar_web.mjs:9,13`, `README.md:111-113` |

Dónde se guardan los datos:
- Base: `VAR/kauta.db` (SQLite) o el Postgres de `KAUTA_BD`. `VAR` por defecto es `kauta/var` (`config.py:24`).
- Claves de demo: `VAR/kauta_clave_datos.key`, `..._firma.key`, `..._auditoria.key` (`config.py:37`).
- Archivos subidos: `VAR/archivos/<sha256><ext>` (`agente.py:37,118-125`).
- Vistas previas cacheadas: `VAR/vistas/<hash>.png` (`negocio.py:88`).
- Registro JSONL (solo scripts/Streamlit): `salidas/registro.jsonl` (`scripts/correr_set.py:7`).

Arranque del servidor (`main.py:29-35`): al iniciar crea tablas, usuarios, invitación de ejemplo, organización, 15 beneficiarios, regla v1, wallet (depósito de 120.000 USD en `operativa`, de los cuales 15.000 se trasladan a `cxp`: `semilla.py:122-124`), y procesa las 20 facturas (`semilla.py:77-137,140-146`). Si `KAUTA_PREPARAR_RECORRIDO=1` y modo demo, prepara el recorrido (`main.py:33-34`).

Restricción de proceso: un solo worker, por candado en memoria (`servicios/__init__.py:4-6`; `README.md:92`).

---

## 15. Datos (`kauta/data`)

- `empresa.json`: Brisamar Labs Inc., Delaware C-Corp ficticia, EIN 88-4410273 (ficticio), Miami, SaaS de logística; "aprobadora" Mariana Torres, Finance Lead; `pagos_mes_promedio` 20 (`empresa.json:2-14`).
- `beneficiarios.json`: 15 beneficiarios (14 activos, 1 bloqueado `X01` Servicios Rápidos Global Ltd.); contratos: 13 `fijo_mensual`, 1 `por_horas` (Legal Puente, USD 150/h); países: 8 CO, 3 US, 3 MX, 1 AR. Cada uno trae `id_fiscal`, `cuenta_registrada` (4 dígitos), `contrato`, `contactos`, `estado` (conteos calculados leyendo el JSON).
- `reglas.json`: sección 6.
- `tarifas.json`: sección 10.
- `facturas/`: 20 archivos `F01` a `F20`: 9 PDF, 6 correo `.eml`, 3 chat `.txt`, 2 imagen (`F13.jpg`, `F17.png`) (columna `canal` de `esperado.csv`). `previews/`: 14 PNG.
- `esperado.csv` (20 filas): decisión esperada **pagar 9, escalar 6, frenar 5**; tipo de caso: 9 normal y 11 trampa.

| Decisión esperada | Facturas | Regla principal |
|---|---|---|
| pagar (9) | F01, F02, F03, F04, F05, F06, F15, F17, F20 | — |
| frenar (5) | F07 (R03), F11 (R05), F14 (R09), F18 (R12), F19 (R04) | una cada una |
| escalar (6) | F08 (R06), F09 (R08), F10 (R10), F12 (R07), F13 (R01), F16 (R11) | una cada una |

Evidencia: `esperado.csv:2-21`.
- `referencia_extracciones.json`: 20 entradas indexadas por nombre de archivo, con `factura_id`, `canal`, `recibida`, beneficiario, número, fechas, moneda, monto, cuenta, confianza y alertas (`:1-...`; F13 tiene confianza de monto 0,52 según `esperado.csv:14`).
- `sorpresa/` (4 archivos + `esperado_sorpresa.csv`): S01 CFDI 4.0 de la misma factura F04 (pagar sola, frenar R03 después del set); S02 ZIP DIAN con el XML y PDF de F02 (R03 después del set); S03 XML con patrón XXE (escalar R01); S04 nota crédito CFDI (frenar R01) (`esperado_sorpresa.csv:2-5`).
- Los datos son ficticios (`servicios/semilla.py:4`; `data/empresa.json:3`).

---

## 16. Historial (`git log`)

| Commit | Fecha | Mensaje | Cambios |
|---|---|---|---|
| `c5c9713` | 2026-10-16 | docs: agregar alcance del reto y responsabilidades del equipo | `README.md` (+191), único archivo |
| `ce7ffa8` | 2026-10-17 | feat: agregar prototipos UX y biblioteca multiformato de facturas | `README.md` ampliado; `prototipos/` con 4 HTML (biblioteca, monitor, planificador, revisor), logos y fuente Inter (+607 -3, 10 archivos) |
| `ffbc43a` | 2026-10-17 | feat(kauta): importar Kauta con 3 roles, entrada por persona y control de reevaluación | Importa toda la app `kauta/` (145 archivos, +18450): núcleo, servidor, front React, datos, pruebas, Docker; `docs/designs/kauta-finops-rediseno.md` (1356 líneas), `TODOS.md` |
| `b1ee286` | 2026-10-17 | feat(kauta): libro de costos y métricas FinOps con una sola fuente | `data/tarifas.json`; `servicios/costos.py` (133), `servicios/metricas.py` (368); `modelos.py` (+51, tabla `eventos_costo`); `test_costos.py` (100); +76 en `test_servidor.py` (11 archivos, +775 -50) |
| `7a9e108` | 2026-10-17 | feat(kauta): completar demo FinOps y preparar importación en Vercel | Elimina `Login.tsx` y `Personas.tsx`; reescribe `App.tsx`, `Resumen.tsx`, `Seguridad.tsx`; agrega `Rendimiento.tsx`, `ReciboFactura.tsx`, `ops/*`, `web/vercel.json`, `web/.nvmrc`, `scripts/probar_web.mjs`, `tests/conftest.py`, `DESIGN.md`, `docs/designs/kauta-estado-2026-10-17.md`; `KAUTA_ORIGENES_ADICIONALES` y `KAUTA_PREPARAR_RECORRIDO` (39 archivos, +1117 -1115) |

Cinco commits en total; rama `main`; remoto `origin` = `https://github.com/FilipaoVfx/hackaton30xBlinka.git`. Archivo sin versionar: `docs/PRD.md`.

---

## 17. Discrepancias y faltantes

### Entre documentos y código

| # | Documento dice | Código hace | Evidencia |
|---|---|---|---|
| 1 | `../README.md` (brief del reto) describe estados `APROBADO_SIMULADO`, `FRENADO`, `PENDIENTE_APROBACION`, reglas de ejemplo con umbral USD 1.000, límite USD 3.000, presupuesto USD 10.000 y "USD para el primer flujo" | El código usa `pagar/frenar/escalar`, umbral 3.000, máximo 10.000, presupuesto 15.000 y tres monedas (USD, COP, MXN) | `../README.md:90-107` vs `reglas.json:12-19`, `motor.py:23` |
| 2 | `../README.md` dice "El agente conectado a documentos reales y sus pruebas de backend quedan pendientes" y no nombra `kauta/` (0 menciones de "kauta") | Existe la app completa en `kauta/` con 76 casos de prueba | `../README.md:243`; 0 menciones de "kauta" en `../README.md` |
| 3 | `kauta/README.md:102` instala `pytest httpx` | `requirements.txt:5` pide `httpx2>=2.0` (si existe ese paquete: NO VERIFICADO; no hay red en esta lectura) | `README.md:102` vs `requirements.txt:5` |
| 4 | `kauta/README.md:129-130`: la API de contraseñas, invitaciones y TOTP "no forma parte de la interfaz pública" | Los endpoints siguen montados y activos; la pantalla ya no los llama. `/api/personas/registro` es público con límite de tasa | `main.py:54-55`, `personas.py:46` |
| 5 | `permisos.py:18` dice que `usuarios.gestionar` "solo existe por API" | Coherente; además `GET /api/auth/demo` entrega la contraseña de demo sin sesión en modo demo | `auth.py:114-121` |
| 6 | `modelos.py:9` "Las tablas de auditoría y del libro mayor solo reciben INSERT" | No hay mecanismo de BD que lo imponga; `restablecer` las borra en demo | sección 5 |
| 7 | El modelo define la tabla `idempotencia` (`ClaveIdempotencia`) | Ninguna ruta ni servicio la escribe ni la lee | `modelos.py:352`, sección 5 |
| 8 | Texto de `/api/seguridad`: "Límites de peticiones por IP, cuenta y usuario (inicio de sesión, cargas y simulador)" | Correcto en esas rutas; ningún otro endpoint tiene límite (p. ej. `/auth/mfa/*`, `/pagos/*`, `/reglas`) | `control.py:123`, sección 9 |
| 9 | `/api/seguridad` lista cada control con estado "activo" | La lista es texto fijo; solo los estados de TOTP, OCR, cadena de auditoría, libro y secretos se calculan | `control.py:95-125` |
| 10 | `empresa.json` nombra como aprobadora a "Mariana Torres, Finance Lead"; versión 1 de reglas dice `creada_por="Mariana Torres (Finance Lead)"` | En las personas de demo Mariana Torres es **CEO**; la CFO es Carlos Rivera | `empresa.json:9-13`, `semilla.py:119,30-31` |
| 11 | `kauta/README.md:40`: "El set oficial empieza con 9 pagadas, 5 frenadas y 6 pendientes" | Coincide con `esperado.csv` (9/5/6); la comprobación en ejecución la hace `test_set_oficial_20_de_20` (no ejecutada aquí) | `esperado.csv`, `test_servidor.py:44` |
| 12 | Costos: pantallas y README hablan de "desglose de lectura XML/texto/OCR/IA" como si reflejara el lector real | El costo de lectura se deduce de la extensión y la confianza, no del lector real; los PDF del set cuestan "texto" aunque se lean de referencia; la IA es simulada | `costos.py:73-84`, `metricas.py:264` |
| 13 | `tarifas.json` define `usd_por_millon_cache` | Nunca se lee | `costos.py:107-113` |
| 14 | `web/src/api.ts:264`: `puede()` acepta `rol === "admin"` | No existe el rol `admin` (solo `ceo`, `cfo`, `cto`) | `permisos.py:10`, `modelos.py:59` |
| 15 | `vistas.plazo` compara contra "hoy" | Para vencimientos de octubre de 2026 usa la fecha fija 2026-10-17 | `vistas.py:72` |
| 16 | `kauta/README.md:13-15` y `DESIGN.md:35` describen el selector sin contraseña | Coincide; `Seguridad.tsx` lo declara ("Esta demo no autentica identidad"), pero el modelo de seguridad de producción (login + TOTP obligatorio para aprobar) no tiene pantalla | `Seguridad.tsx:9` |
| 17 | `config.py:13` "En producción, si falta una clave el servidor NO arranca" | Cierto; pero también en producción `/auth/persona` da 404 y el front no tiene login: la app no es utilizable en `produccion` con la pantalla actual | `config.py:34-35`, `auth.py:95-96`, `App.tsx:38-42` |
| 19 | `Dockerfile` copia `kauta/`, `servidor/`, `data/` y `web/dist` | No copia `static/` ni `assets/` (usados por Streamlit) ni `tests/` ni `scripts/`; coherente con el servidor, no con el plan B Streamlit dentro de la imagen | `Dockerfile:21-24` |
| 20 | `kauta/README.md:131`: "El plan B Streamlit sigue disponible con `requirements.txt`" | `app.py` usa `kauta/agente.py` en memoria (sin base de datos, sin roles, sin pagos, sin costos); es una aplicación distinta, con 5 páginas (tablero, bandeja, reglas, registro, validación) | `app.py:25-30`, `app.py` funciones `pagina_*` |

### Cosas que parecen faltar para lo que promete el README

- Login real y gestión de personas en la pantalla (existen endpoints; la pantalla no) — `../docs/designs/kauta-estado-2026-10-17.md:78-81` explica que la API se conserva por la decisión D8.
- Lectura real por OCR/IA del set: el set se resuelve por tabla de referencia; para documentos nuevos (PDF, foto, correo) hace falta Tesseract o la clave de Anthropic (`servicios/agente.py:68-69`). La medición de precisión del OCR vive en un script, no en una prueba (`scripts/medir_ocr.py`); la prueba de servidor del lector local es `test_lector_local_sin_ia` (`tests/test_servidor.py:225`).
- Concurrencia entre procesos: el brief pide "presupuesto bajo concurrencia" (`../README.md:207`); el código lo resuelve con un candado de hilos local al proceso y un saldo calculado, no con bloqueo de base (comentario de futuro en `servicios/__init__.py:4-5`).
- Migraciones de base de datos: NO ENCONTRADO (solo `create_all`).
- Integración continua: NO ENCONTRADO (`../TODOS.md:5-15`).
- Registro de tokens reales de la IA: NO ENCONTRADO (los costos de IA son simulados).
- Despliegue en Vercel: no confirmado; `../docs/designs/kauta-estado-2026-10-17.md:17-19` dice que falta la URL para autorizar el origen. El archivo `web/vercel.json` apunta al host `kauta.2-25-233-186.sslip.io`.
- Ejecución verificada de las pruebas: esta ficha no las corrió; la cifra de 76 sale de contar funciones y casos parametrizados y coincide con el documento de estado.
- Internacionalización: toda la interfaz está en español; sin archivos de traducción (NO ENCONTRADO).
- Pantalla para pagos por riel, aprobaciones por lote o filtros avanzados: NO ENCONTRADO (no hay).
