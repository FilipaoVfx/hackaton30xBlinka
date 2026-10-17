# Kauta · el agente que paga por la empresa

Kauta lee las facturas que llegan por correo, chat, PDF, foto o XML fiscal; las revisa contra
13 reglas de la empresa; paga desde la wallet lo que cumple, frena lo que rompe una regla dura y
le pregunta a una persona todo lo demás. Varias personas con su propio usuario, su rol y su
contraseña; la pantalla funciona igual en celular, tableta y computador. Proyecto del **Reto Blinka · Hackathon 30X**
(16 al 18 de octubre de 2026). Equipo: Luis, Juan, Mauricio y Laura.

> **Principio:** la IA lee, el código decide. El modelo solo extrae datos; un motor de 13 reglas
> deterministas toma la decisión, y el pago tiene sus propios controles. Ningún pago depende de lo
> que diga el modelo ni de lo que diga el documento.

## Resultados

| Criterio del reto | Resultado |
|---|---|
| Autonomía | 14 de 20 facturas del set resueltas solas (70 %); las otras 6 las exige la política |
| Seguridad | 0 pagos fuera de reglas · 11 de 11 trampas detenidas · año simulado: 175 facturas y 0 pagos indebidos según un verificador independiente |
| Explicabilidad | 100 % de las decisiones con motivo en lenguaje claro y las 13 reglas evaluadas |
| Exactitud | 20 de 20 decisiones iguales a `data/esperado.csv` · 58 pruebas automáticas en verde |
| Lectura local | 92 % de los campos leídos con OCR, sin IA y sin que el documento salga del servidor (`scripts/medir_ocr.py`) |

## Cómo correrlo en Visual Studio Code

1. **Descomprima** `kauta-kit-v2.zip` y abra la carpeta `kauta` en VS Code (**Archivo → Abrir carpeta**).
2. Instale la extensión **Python** de Microsoft si no la tiene (VS Code la sugiere solo al abrir el proyecto).
3. Cree el entorno: `Ctrl+Shift+P` → **Python: Create Environment** → *Venv* → su Python 3.11 o superior.
   VS Code lo selecciona solo y ofrece instalar `requirements.txt`: diga que sí. Si no lo ofrece,
   `Ctrl+Shift+P` → **Tasks: Run Task** → *1 · Instalar dependencias*.
4. Pulse **F5** y elija *Kauta · servidor (abre el navegador)*. Se abre `http://localhost:8000`.
5. Entre con un clic en cualquiera de las personas de prueba (contraseña `Kauta-30X-demo-2026`).

**La demo arranca con datos, no vacía.** La primera vez que corre, Kauta crea la base, siembra la empresa,
los 15 beneficiarios, las reglas, la wallet fondeada y **procesa las 20 facturas del set**: verá 9 pagadas,
5 frenadas y 6 esperando a una persona. Si alguna vez la ve vacía, entre como *Jurado Hackathon 30X* o
*Equipo Kauta* y pulse **«Restablecer la demo» → «Con las 20 facturas del set»**; o corra la tarea
*4 · Volver la demo al inicio* y arranque de nuevo.

Otras tareas listas en `Ctrl+Shift+P` → **Tasks: Run Task**: correr las 58 pruebas, arrancar el servidor
sin depurador y medir el lector local (OCR).

## Cómo correrlo desde la terminal

Requiere Python 3.11 o superior. La pantalla ya viene compilada en `web/dist`: no hace falta Node.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate        macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn servidor.main:app --port 8000     # abra http://localhost:8000
python -m pytest -q                       # 58 pruebas
```

En la pantalla de inicio hay botones para entrar como cada persona de prueba
(contraseña de la demo: `Kauta-30X-demo-2026`):

| Persona | Rol | Para qué sirve en la demo |
|---|---|---|
| Mariana Torres · Finance Lead | Aprobación | Responde lo que Kauta escala y edita reglas |
| Carlos Rivera · CFO | Aprobación | Segunda firma en montos altos (doble control) |
| Andrea Gómez · Analista | Carga | Carga facturas; no puede aprobarlas (segregación) |
| Tomás Herrera · Tesorería | Tesorería | Fondea la wallet y reintenta pagos devueltos |
| Sofía Lara · Auditora | Solo lectura | Revisa y exporta la auditoría |
| Jurado Hackathon 30X | Jurado | Usa el simulador, aprueba casos y restablece la demo |
| Equipo Kauta | Administración | Invita personas, cambia roles y desactiva cuentas |

Para agregar a alguien: entre como **Equipo Kauta** → «Personas y roles» → «Invitar persona». Kauta
genera un código de un solo uso; esa persona lo usa en «Crear cuenta» y entra con el rol que se le
asignó. Nadie se da de alta solo ni elige su propio rol.

**Con Docker y PostgreSQL:** copie `.env.example` como `.env` y ejecute `docker compose up --build`.
**Para cambiar la pantalla:** `cd web && npm install && npm run dev` (Vite en el puerto 5173, con la API en el 8000).
**Plan B sin servidor web:** `streamlit run app.py` (la pantalla original, con el mismo motor).
**Modo IA:** defina `ANTHROPIC_API_KEY` para que la IA lea lo que el lector local no logre. El modelo se
cambia con `KAUTA_MODELO`. Orden de lectura: **XML fiscal exacto → texto del PDF → OCR local → IA**.

**Lector local (OCR):** necesita Tesseract con español e inglés instalado en el sistema:
`sudo apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng` (en macOS,
`brew install tesseract tesseract-lang`). Sin él, Kauta funciona igual con los demás lectores.
Para medirlo contra el set: `python scripts/medir_ocr.py`.

## Qué trae

- **Bandeja de facturas** con la decisión, el motivo y la tira de las 13 reglas de cada una; carga de PDF, foto, correo, chat, XML y ZIP.
- **Kauta pregunta:** una pregunta concreta por cada regla que falló, con plazo y riel de pago; doble aprobación sobre el umbral.
- **Simulador de pagos:** 14 casos (normales, trampas, ataques y controles) o una factura armada a mano; si se paga, el dinero viaja por ACH, wire, SWIFT, SPEI, Bre-B, Pix o USDC con cambio de moneda, comisión y comprobante. «Simular un año» corre cientos de facturas con un verificador independiente.
- **Wallet:** libro mayor de doble partida (operativa → sub-wallet de pagos → reservas → tránsito → pagado), fondeo por periodo y pagos devueltos.
- **Proveedores:** contratos, rieles y verificación de cambios de cuenta por un canal independiente.
- **Reglas** versionadas con «qué cambiaría» antes de guardar y reevaluación automática.
- **Auditoría** encadenada con HMAC-SHA256 y exportación; **Seguridad** con los controles, el segundo factor y las sesiones.
- **Personas y roles:** invitación con código de un solo uso, registro de la propia persona, cambio de rol, desactivación (que cierra sus sesiones) y desbloqueo.
- **Lector local sin IA:** fotos y PDF escaneados se leen con OCR **dentro del servidor** (Tesseract, español e inglés). El documento no sale de la empresa, no cuesta por página y funciona sin internet. La IA solo se llama si el lector local no alcanza la confianza mínima.

## Estructura

```
kauta/                 núcleo del agente (sin dependencias web)
  motor.py             13 reglas deterministas: pagar, frenar o escalar
  extractor.py         lectura: XML fiscal sin IA, set de referencia o IA; validaciones deterministas
  lectores_xml.py      CFDI 4.0, DIAN UBL 2.1 y AttachedDocument, ZIP seguro, QR de SAT, DIAN y ARCA
  normalizacion.py     factura canónica y validadores (NIT, RFC, CUIT, CNPJ, RUT, RUC, ABA, CLABE, CBU, IBAN…)
  ocr.py               lector local: OCR de fotos y PDF escaneados + extracción de campos por reglas
  agente.py, registro.py, ui.py   agente en memoria y pantalla Streamlit (plan B)
servidor/              API FastAPI con base de datos
  main.py              aplicación, middleware y archivos de la pantalla
  modelos.py           esquema de la base de datos (SQLAlchemy 2.0)
  esquemas.py          validación de entradas (Pydantic v2)
  seguridad/           contraseñas Argon2id, sesiones y CSRF, roles, cifrado AES-256-GCM, firmas HMAC, TOTP, límites, cabeceras
  servicios/           agente con base de datos, wallet, pagos y rieles, simulador, auditoría, personas, semilla
  rutas/               endpoints por dominio (auth, negocio, dinero, simulador, control)
web/                   pantalla React 19 + TypeScript + Tailwind v4 (adaptable a celular, tableta y computador)
data/                  empresa, reglas, beneficiarios, 20 facturas, 3 archivos sorpresa y resultados esperados
scripts/               generar el set, correr el set, medir la IA y el OCR, capturas y prueba clic a clic
tests/                 núcleo, formatos fiscales y servidor
```

## Datos y seguridad

Todos los datos son ficticios: empresa, personas, identificaciones (con dígito de verificación
válido), cuentas y correos (dominios `example`). Cada documento dice «Documento simulado · sin validez
fiscal». No se mueve dinero real. La clave de la API nunca va al repositorio: use variables de
entorno. En modo demo las claves de cifrado se generan en `var/`; en producción el servidor no
arranca sin ellas.
