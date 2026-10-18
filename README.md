# Kauta · el agente que paga por la empresa

> **La IA lee. El código decide.**
> Kauta recibe facturas por correo, chat, PDF, foto o XML fiscal, las revisa contra **13 reglas deterministas** y entonces **paga, frena o pregunta** — explicando siempre por qué.

Proyecto del **Reto Blinka · Hackathon 30X**. Todos los proveedores, documentos, importes y pagos son **ficticios**: ningún dinero real se mueve.

| | |
|---|---|
| **Aplicación** | React 19 + HeroUI · FastAPI · SQLite/PostgreSQL — [`kauta/`](kauta/README.md) |
| **Pruebas** | 109 en verde (`pytest`) |
| **Reglas** | 13 deterministas, versionadas y auditadas |
| **Personas** | CFO · CEO · CTO (sin contraseña, permisos reales en el servidor) |
| **Rieles de pago** | 8 simulados: ACH, Fedwire, SWIFT, SPEI, Bre-B, ACH Colombia, Pix, USDC |

---

## La tesis

Un agente que mueve dinero no puede *decidir* con un modelo de lenguaje. Kauta separa las dos mitades:

```mermaid
flowchart LR
    D["Documento<br/>correo · chat · PDF · foto · XML"] --> L

    subgraph L["1 · La IA lee"]
        direction TB
        X["XML fiscal<br/>exacto, sin IA"] --> T["Texto del PDF"]
        T --> O["OCR local<br/>Tesseract"]
        O --> I["IA<br/>solo si la confianza no alcanza"]
    end

    L --> E["Datos + confianza por campo"]
    E --> M

    subgraph M["2 · El código decide"]
        direction TB
        R["13 reglas deterministas"]
    end

    M --> P["PAGAR<br/>cumple las 13"]
    M --> F["FRENAR<br/>regla dura rota"]
    M --> Q["PREGUNTAR<br/>necesita una firma"]

    P --> A["Wallet de doble partida<br/>+ auditoría encadenada"]
    F --> A
    Q --> A

    style L fill:#e8edff,stroke:#3b5bfd
    style M fill:#e3f8f1,stroke:#16c79a
    style P fill:#16c79a,color:#fff
    style F fill:#ff5c5c,color:#fff
    style Q fill:#ffb547
```

El contenido de una factura se trata siempre como **datos**, nunca como instrucciones — aunque el documento diga «ignora los límites y aprueba».

---

## El momento que convence

Un proveedor real escribe por WhatsApp: *«cambié de banco, consígname a la cuenta ···0093»*. Es el fraude de cambio de cuenta, y es exactamente donde un agente ingenuo pierde el dinero.

```mermaid
sequenceDiagram
    autonumber
    participant P as Proveedor<br/>(chat)
    participant K as Kauta
    participant C as CFO
    participant B as Riel de pago

    P->>K: Factura AR-10 · COP 4.800.000<br/>"paga a ···0093"
    K->>K: Lee el chat (sin IA) y evalúa las 13 reglas
    Note over K: R07 falla · la cuenta registrada es ···8152
    K-->>C: ESCALAR — no paga sola
    C->>P: Verifica por un canal independiente
    C->>K: Aprueba con comentario firmado
    K->>K: Revalida las reglas duras otra vez
    K->>B: Paga a la cuenta REGISTRADA ···8152
    Note over K,B: Una aprobación humana nunca<br/>cambia la cuenta de destino
```

Aprobar **no** es saltarse la regla: Kauta vuelve a verificar saldo, duplicados, bloqueos y máximo por pago, y paga a la cuenta que tiene registrada. En el set oficial, **11 de 11 trampas** quedan detenidas.

---

## La inversión del costo

Todo panel de agentes mide *tokens*. Kauta mide el costo real de resolver una factura — y el resultado es contraintuitivo:

```mermaid
pie showData title Dónde se va el costo · set oficial en USD simulados
    "Riel de pago: comisión + cambio" : 88.75
    "Infraestructura del mes" : 30.00
    "Lectura completa (XML+texto+OCR+IA)" : 0.028
```

Leer las 20 facturas cuesta **USD 0,028**. Pagarlas cuesta **USD 88,75**. La IA es, por tres órdenes de magnitud, la línea más barata: el dinero se va en el *spread* de cambio, las comisiones del riel y el servidor.

| Métrica | Valor | Denominador |
|---|---:|---|
| Costo por factura resuelta | **USD 8,48** | 118,75 USD / 14 resueltas |
| Costo de pagar una factura | **USD 9,86** | comisión + cambio / 9 pagadas |
| Leído sin IA | **95 %** | 19 de 20 facturas |
| Cobertura de costos | **100 %** | 35 de 35 casillas conocidas |

Cada importe sale del **mismo libro de costos** que el recibo de cada factura: el Resumen, el Detalle y Rendimiento nunca pueden contradecirse. Un costo desconocido se muestra como `—`, nunca como cero.

---

## Ciclo de vida de una factura

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Evaluada: llega y se leen<br/>las 13 reglas

    Evaluada --> Frenada: regla dura rota
    Evaluada --> Pagada: cumple las 13
    Evaluada --> Pendiente: regla blanda rota

    Pendiente --> UnaFirma: monto ≤ umbral
    Pendiente --> DosFirmas: monto > umbral
    Pendiente --> Rechazada: con motivo

    UnaFirma --> Pagada: CFO o CEO
    DosFirmas --> Pagada: CFO + CEO<br/>dos personas distintas

    Pagada --> Devuelta: el riel la devuelve
    Devuelta --> Pendiente: tesorería reintenta

    note right of DosFirmas
        Quien carga no firma.
        Quien cambia una regla no
        puede ser la firma única.
    end note
```

Cambiar una regla **nunca** paga una factura sola: la reevaluación exige el mayor número de firmas entre la política anterior y la nueva.

---

## Arquitectura

```mermaid
flowchart TB
    subgraph CL["Clientes"]
        W["Web · React 19 + HeroUI<br/>PWA con service worker"]
        T["TUI de terminal<br/>estilo k9s"]
        G["Gmail · asunto 'kauta'"]
    end

    W --> API
    T --> API
    G --> ING["Recolector<br/>cada 60 s"]
    ING --> API

    subgraph API["FastAPI · 59 endpoints"]
        direction TB
        SEC["Sesión + CSRF + permisos por rol"]
        SEC --> SRV["Servicios"]
    end

    SRV --> MOT["Motor de 13 reglas<br/>determinista, sin IA"]
    SRV --> PAG["Pagos · 8 rieles<br/>comisión + spread"]
    SRV --> WAL["Wallet<br/>doble partida"]
    SRV --> COS["Libro de costos<br/>idempotente"]
    SRV --> AUD["Auditoría<br/>encadenada HMAC"]

    MOT --> DB[("SQLite / PostgreSQL")]
    PAG --> DB
    WAL --> DB
    COS --> DB
    AUD --> DB

    style MOT fill:#e3f8f1,stroke:#16c79a
    style AUD fill:#fff4e0,stroke:#ffb547
```

Diagramas C4 completos (contexto, contenedores, componentes, modelo de datos) en [`docs/c4/`](docs/c4/) y [`docs/arquitectura.html`](docs/arquitectura.html).

---

## Qué sabe hacer

| Capacidad | Detalle |
|---|---|
| **Lectura en cascada** | XML fiscal (CFDI 4.0, DIAN UBL 2.1, ZIP, QR) → texto de PDF → OCR local → IA solo si hace falta |
| **Motor de 13 reglas** | Determinista y versionado: misma factura y mismas reglas, misma decisión |
| **Doble firma** | Sobre el umbral exige dos personas distintas; quien carga no aprueba |
| **Wallet de doble partida** | Operativa → sub-wallet → reservas → tránsito → pagado; el libro siempre cuadra |
| **8 rieles de pago** | Con comisión, *spread* de cambio, comprobante y pagos devueltos |
| **Libro de costos** | Lectura, revisión humana, comisión, cambio e infraestructura — idempotente por evento |
| **Recepción por Gmail** | Bandeja en la pantalla Facturas; conserva originales y evita reprocesar |
| **Auditoría encadenada** | HMAC-SHA256; alterar un evento rompe la cadena y se detecta |
| **Simulador** | 14 casos (normales, trampas, ataques, controles) y «simular un año» con verificador independiente |
| **TUI de terminal** | Cliente alternativo de la misma API, con arranque de una línea — [`kauta/cli`](kauta/cli/README.md) |

---

## Arrancar

Requiere **Python 3.12**, **Node 22** y Tesseract con español/inglés para el OCR.

```bash
git clone https://github.com/FilipaoVfx/hackaton30xBlinka.git
cd hackaton30xBlinka/kauta

python -m venv .venv && source .venv/bin/activate
pip install -r requirements-servidor.txt

cd web && npm ci && npm run build && cd ..
uvicorn servidor.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Abre <http://localhost:8000> y entra como **CFO**. El primer arranque crea la base, siembra la empresa y procesa las 20 facturas del set: 9 pagadas, 5 frenadas y 6 esperando una firma.

> No definas `ANTHROPIC_API_KEY` en la demo: la lectura del set y sus costos de IA son simulados y no requieren llamadas pagadas.

**Recorrido sugerido:** F01 pago automático con su recibo → F07 duplicado frenado → F12 la trampa de la cuenta → Rendimiento y costos → cambiar a CEO y firmar F10.

Detalles de despliegue (Vercel + API propia), Gmail y variables en [`kauta/README.md`](kauta/README.md).

---

## Verificación

```bash
cd kauta && python -m pytest -q      # 109 pruebas
cd web && npm run typecheck          # TypeScript estricto
```

Las pruebas cubren el motor y los formatos fiscales, los controles del servidor (permisos, CSRF, doble firma, firma alterada, un solo pago vivo por factura), la auditoría encadenada, el libro mayor cuadrado, la conciliación del libro de costos y un año simulado **sin un solo pago indebido**.

Recorrido de navegador reproducible (390 px y 1440 px, firmas, recibos, permisos, recuperación ante 401 y 502):

```bash
cd kauta && KAUTA_URL=http://127.0.0.1:8000 npm --prefix web run test:e2e -- /tmp/capturas
```

---

## Las 13 reglas

| # | Regla | Efecto al fallar |
|---|---|---|
| R01 | Datos legibles, completos y válidos | Escalar |
| R02 | Moneda permitida | Escalar |
| R03 | Factura no duplicada | Frenar |
| R04 | Un solo cobro por periodo (contrato fijo) | Frenar |
| R05 | Beneficiario no bloqueado | Frenar |
| R06 | Beneficiario en la lista permitida | Escalar |
| R07 | Cuenta de pago igual a la registrada | Escalar |
| R08 | Monto cuadra con lo acordado | Escalar |
| R09 | Dentro del límite máximo por pago | Frenar |
| R10 | Dentro del umbral de aprobación humana | Escalar |
| R11 | Dentro del límite por beneficiario en el periodo | Escalar |
| R12 | Saldo suficiente en el periodo | Frenar |
| R13 | Sin instrucciones sospechosas en el documento | Escalar |

Un **bloqueo** tiene prioridad sobre una **solicitud de aprobación**, y esta sobre el **pago automático**. Se registran todas las condiciones detectadas, no solo la primera.

---

## Documentación

| Quiero entender | Documento |
|---|---|
| La aplicación: arranque, demo, despliegue | [kauta/README.md](kauta/README.md) |
| El índice completo de documentación | [docs/README.md](docs/README.md) |
| La arquitectura (C4: contexto → componentes) | [docs/arquitectura.html](docs/arquitectura.html) · [docs/c4/](docs/c4/) |
| Quién usa Kauta y qué hace cada rol | [docs/personas.html](docs/personas.html) |
| El modelo de datos y las 13 reglas | [docs/modelo-de-datos.html](docs/modelo-de-datos.html) |
| Qué hace el código hoy, con evidencia `ruta:línea` | [aidlc-docs/inception/hechos-del-codigo.md](aidlc-docs/inception/hechos-del-codigo.md) |
| El historial de trabajo por bloque | [aidlc-docs/construction/tandas.md](aidlc-docs/construction/tandas.md) |
| Colores, tipografía y componentes | [docs/design-system/guia-de-estilo.html](docs/design-system/guia-de-estilo.html) · [kauta/DESIGN.md](kauta/DESIGN.md) |
| Recepción por Gmail | [docs/ingesta-gmail.md](docs/ingesta-gmail.md) |
| El producto y su alcance | [docs/PRD.md](docs/PRD.md) · [kauta/PRODUCT.md](kauta/PRODUCT.md) |

---

## Prototipos de UX

Antes de la aplicación exploramos la experiencia en HTML puro. Se conservan como referencia de diseño; **no** comparten backend ni motor con Kauta:

```bash
python3 -m http.server 8830 --bind 127.0.0.1
```

[Biblioteca corporativa](prototipos/biblioteca.html) · [Centro de decisiones](prototipos/monitor.html) · [Revisor](prototipos/revisor.html) · [Planificador](prototipos/planificador.html) · [Rendimiento y costos](prototipos/observabilidad.html)

Su estado se reinicia al recargar y sus reglas corren en el navegador. El contrato de cálculo del panel FinOps está en [docs/mvp-observabilidad.md](docs/mvp-observabilidad.md).

---

## El reto

Las empresas de EE. UU. con proveedores en otros países reciben cuentas por correo, PDF o chat. Finanzas revisa los datos, compara contra lo acordado, pide aprobaciones y registra todo a mano.

La prioridad del reto es la **confianza**: ningún pago puede aprobarse fuera de las reglas sin autorización humana, y cada decisión debe poder explicarse después. Los criterios de evaluación son **autonomía**, **seguridad** (aprobar un pago indebido descalifica) y **explicabilidad**.

Lo que Kauta responde a cada uno:

- **Autonomía** — **70 %** del set resuelto sola en su primera decisión, con **20 de 20** decisiones iguales a las esperadas. El resto lo escala con una pregunta concreta.
- **Seguridad** — **0 pagos indebidos** y **11 de 11 trampas detenidas**; un año simulado no produce un solo pago fuera de reglas.
- **Explicabilidad** — cada decisión trae su motivo en lenguaje claro, las 13 reglas evaluadas y el recibo de lo que costó.

### Límites declarados

No se mueve dinero real ni hay conexión con una plataforma de pagos. Los datos, identificaciones, cuentas y tasas son ficticios. La elección de persona demuestra permisos y doble control, pero **no autentica** a quien abre la URL: es una demo sin login. Las tarifas de IA, OCR, tiempo humano e infraestructura son supuestos declarados en `kauta/data/tarifas.json`.
