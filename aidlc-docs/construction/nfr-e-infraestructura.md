# Requisitos no funcionales e infraestructura

Describe cómo se despliega y qué garantías no funcionales tiene Kauta hoy. Fuente: `aidlc-docs/inception/hechos-del-codigo.md` §14 y §9, más los archivos `kauta/Dockerfile`, `kauta/ops/*` y `kauta/web/vercel.json`. Todos los datos son ficticios; no hay dinero real.

## Pila (hechos §1)

| Capa | Hoy (construido) |
|---|---|
| Servidor | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 (`requirements-servidor.txt:2-6`) |
| Base de datos | SQLite en `VAR/kauta.db` con WAL; PostgreSQL opcional por `KAUTA_BD` (`servidor/config.py:76`, `servidor/db.py:19-26`) |
| Front | React 19, Vite, Tailwind 4, TypeScript estricto, Node 22 (`web/package.json`) |
| Lectura de documentos | Tesseract (sistema), IA de Anthropic solo si hay `ANTHROPIC_API_KEY` |
| Versiones | servidor 2.1.0; web 2.0.0 (`servidor/config.py:58`, `web/package.json:4`) |

## Topología de despliegue

| Pieza | Dónde corre | Archivo |
|---|---|---|
| API y SQLite | Servidor propio, servicio `kauta.service`, un solo proceso, puerto 8840 en 127.0.0.1 | `ops/kauta.service:8-18` |
| Proxy HTTPS | nginx; 80 redirige a 443; Let's Encrypt; `client_max_body_size 12m`; `proxy_read_timeout 120s`; host `kauta.2-25-233-186.sslip.io` | `ops/nginx.kauta:1-27` |
| Front | Vercel (Root Directory `kauta/web`), reenvía `/api/*` por HTTPS al host anterior | `web/vercel.json:6-14` |
| Imagen contenedor | Dos etapas (node:22-alpine compila la web; python:3.12-slim corre uvicorn en 8000), usuario `kauta` uid 10001, `HEALTHCHECK` a `/api/salud` | `Dockerfile:3-28` |
| Compose | `kauta` (solo lectura, `cap_drop ALL`, `no-new-privileges`) y `db` (postgres:17-alpine) | `docker-compose.yml:3-25` |

Estado de Vercel: **NO VERIFICADO**. El estado del 2026-10-17 dice que el usuario lo desplegará y que falta su URL para autorizar el origen (`docs/designs/kauta-estado-2026-10-17.md:17-19`). Modo del servidor desplegado (`demo` o `produccion`): **NO VERIFICADO**; `runtime.env` está fuera del repositorio (`ops/kauta.service:9`).

```
Navegador --> Vercel (React, vercel.json) --/api/*--> nginx 443 --> uvicorn 127.0.0.1:8840 (1 worker) --> SQLite (VAR, fuera del repo)
```

## Variables de entorno (solo nombres, hechos §14)

| Variable | Uso |
|---|---|
| `KAUTA_MODO` | `demo` (por defecto) o `produccion` |
| `KAUTA_BD` | URL de la base |
| `KAUTA_VAR` | carpeta de datos, claves y archivos subidos |
| `KAUTA_CLAVE_DATOS`, `KAUTA_CLAVE_FIRMA`, `KAUTA_CLAVE_AUDITORIA` | tres claves base64 de al menos 32 bytes; en producción faltar una impide arrancar (`config.py:34-35`) |
| `KAUTA_ORIGEN` | origen público; si empieza por `https://` la cookie es `Secure` con nombre `__Host-kauta_sesion` |
| `KAUTA_ORIGENES_ADICIONALES` | orígenes autorizados adicionales (por ejemplo Vercel) |
| `KAUTA_PREPARAR_RECORRIDO` | `1`: presupuesto USD 20.000 y primera firma CFO en F10 (solo demo) |
| `KAUTA_MODELO` | modelo de la API (`claude-sonnet-5-5` por defecto, `extractor.py:33`) |
| `ANTHROPIC_API_KEY` | activa la lectura con IA |
| `POSTGRES_PASSWORD` | contraseña de Postgres en compose |
| `KAUTA_URL`, `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | recorrido Playwright |

## Datos fuera del repositorio

| Dato | Ubicación | Evidencia |
|---|---|---|
| Base | `VAR/kauta.db` (por defecto `kauta/var`; en el servicio, `/root/.local/share/kauta/var`) | `config.py:24,76`, `ops/kauta.service:18` |
| Claves de demo | `VAR/kauta_clave_*.key`, modo 600 | `config.py:37` |
| Archivos subidos | `VAR/archivos/<sha256><ext>` | `servicios/agente.py:118-125` |
| Vistas previas | `VAR/vistas/<hash>.png` | `rutas/negocio.py:88` |
| Variables del servicio | `/root/.config/kauta/runtime.env` (contenido NO ENCONTRADO) | `ops/kauta.service:9` |

## Requisitos no funcionales

| Tema | Hoy (construido) | Evidencia |
|---|---|---|
| Un solo proceso | Obligatorio: el candado `BLOQUEO` y el limitador de tasa viven en memoria del proceso | `servicios/__init__.py:4-6`, `seguridad/limites.py:2-3`, `README.md:92` |
| Concurrencia | Candado de hilos local; no hay bloqueo de base entre procesos | hechos §17 |
| Sesión | Token de 256 bits (solo su SHA-256 en base), 30 min de inactividad, 8 h máximo | `sesiones.py:30-46`, `config.py:55-56` |
| CSRF y Origin | Cabecera `X-CSRF-Token`; Origin validado contra la lista autorizada | `sesiones.py:78-80`, `cabeceras.py:26-30` |
| Cabeceras | CSP estricta, nosniff, DENY, `no-referrer`, HSTS con HTTPS, `no-store` en `/api` (también en `vercel.json:16-55`) | `cabeceras.py:19-45` |
| Cifrado en reposo | AES-256-GCM con AAD ligada al registro (cuentas, TOTP) | `cifrado.py:25-36` |
| Firmas y auditoría | HMAC-SHA256 en aprobaciones y pagos; cadena HMAC en `auditoria` | `firma.py`, `auditoria.py:29-61` |
| Contraseñas | Argon2id, mínimo 15 caracteres; bloqueo a los 5 intentos por 15 min | `contrasenas.py`, `auth.py:23-24` |
| Límites de tasa | Login, registro, carga de archivos y simulador; otros endpoints sin límite | `control.py:123`, hechos §17 #8 |
| Tamaño | Cuerpo máximo 12 MB (413); archivo de factura 10 MB | `main.py:26,44-49`, `negocio.py:126-139` |
| Contenedor y servicio | No root, FS de solo lectura, `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `UMask=0077` | `Dockerfile:13,25`, `ops/kauta.service:14-18` |
| Salida escapada | Sin `innerHTML` ni `dangerouslySetInnerHTML` en `web/src` | búsqueda, hechos §9 |
| Accesibilidad | Botones de 44 px, foco visible, `prefers-reduced-motion` | `kauta/DESIGN.md:37-44` |

## Lo que NO existe hoy

| Faltante | Estado |
|---|---|
| Login real en pantalla y TOTP en pantalla | NO ENCONTRADO; la entrada es el selector sin contraseña (`POST /api/auth/persona`, 404 cuando `CONFIG.demo` es falso: `auth.py:95-96`) |
| Límite de tasa compartido entre procesos, rotación de claves, KMS | NO ENCONTRADO |
| Migraciones de base de datos | NO ENCONTRADO (solo `create_all`) |
| Disparadores que impidan UPDATE y DELETE en auditoría y libro | NO ENCONTRADO; la integridad se comprueba por lectura de la cadena |
| Integración continua | NO ENCONTRADO (`TODOS.md:5-15`) |
| Lockfile de Python | NO ENCONTRADO (rangos `>=`) |
| CORS | NO ENCONTRADO; el modelo es mismo origen o proxy de Vercel |
