---
name: Kauta
description: Autonomía, pero cauta. Interfaz para operar cuentas por pagar.
colors:
  noche: "#0b1736"
  noche-2: "#142350"
  noche-3: "#1e2f63"
  menta: "#16c79a"
  menta-t: "#0b7a5c"
  menta-s: "#e3f8f1"
  ambar: "#ffb547"
  ambar-t: "#9a5800"
  ambar-s: "#fff4e0"
  coral: "#ff5c5c"
  coral-t: "#c7302f"
  coral-s: "#ffe9e9"
  azul: "#3b5bfd"
  azul-t: "#2a44d6"
  azul-s: "#e8edff"
  pizarra: "#5b6782"
  bruma: "#e3e8f2"
  niebla: "#f5f7fb"
  panel: "#ffffff"
typography:
  headline:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "30px"
    fontWeight: 650
    lineHeight: "1.15"
    letterSpacing: "-.04em"
  metric:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "30px"
    fontWeight: 550
    lineHeight: "1.2"
    letterSpacing: "-.04em"
  title:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    letterSpacing: "-.025em"
  body:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "1.45"
  label:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 500
rounded:
  button: "7px"
  panel: "12px"
  table: "10px"
  legacy-panel: "14px"
spacing:
  step-4: "4px"
  step-8: "8px"
  step-12: "12px"
  step-16: "16px"
  step-20: "20px"
  step-24: "24px"
  step-32: "32px"
components:
  button-primary:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.panel}"
    rounded: "{rounded.button}"
    padding: "8px 16px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.noche}"
    rounded: "{rounded.button}"
    padding: "8px 16px"
    height: "44px"
  button-danger:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.coral-t}"
    rounded: "{rounded.button}"
    padding: "8px 16px"
    height: "44px"
  button-ghost:
    textColor: "{colors.pizarra}"
    rounded: "{rounded.button}"
    padding: "8px 16px"
    height: "44px"
  button-success:
    backgroundColor: "{colors.menta-t}"
    textColor: "{colors.panel}"
    rounded: "{rounded.button}"
    padding: "8px 16px"
    height: "44px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.noche}"
    rounded: "{rounded.panel}"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.noche}"
    rounded: "{rounded.table}"
    padding: "8px 12px"
---
# Kauta · Sistema de interfaz

## Overview

**Creative North Star: "Autonomía, pero cauta."**

Kauta es una herramienta para operar cuentas por pagar. La pregunta de cada pantalla manda sobre la cantidad de datos: como máximo cuatro métricas de cabecera; los detalles se abren cuando hacen falta.

La identidad existente se mantiene: modo claro, navegación noche, superficie niebla, panel blanco y semáforo de decisiones. El refinamiento da más peso a la tipografía, reduce los contenedores y muestra el motivo de cada decisión. No introduce una identidad nueva.

**Key Characteristics:**

- Semáforo reservado a decisiones, con texto e iconos.
- Métricas en una fila compartida con separadores.
- Inter Variable local y números tabulares.
- Inspección de reglas guardadas, sin evaluación ficticia.

## Colors

### Primary

Azul para acciones, selección y foco; azul-t para hover y texto de acción, azul-s para selección suave.

### Secondary

Menta para pagar; ámbar para preguntar o escalar; coral para frenar. Las variantes de texto (-t) y superficie (-s) mantienen legibles los estados sobre fondos claros. El inspector oscuro adapta el contraste sin cambiar el significado.

### Neutral

Noche sostiene navegación y texto principal; noche-2 y noche-3 son capas oscuras. Niebla es el lienzo, blanco el panel, pizarra el texto secundario y bruma los separadores.

**The Semáforo Rule.** Menta significa pagar, ámbar preguntar y coral frenar. Azul identifica acciones y selección; nunca informar un estado solo con color.

## Typography

**Display Font / Body Font:** Inter Variable local, con la pila sans del frontmatter. No se introduce una familia de titulares distinta.

- **Headline:** cabeceras compartidas, peso 650; 28 px hasta 640 px. Descripción de 14 px, interlínea 1.55 y máximo 68ch; en móvil, 13 px.
- **Metric:** peso 550; 25 px entre 641 y 1100 px y 26 px hasta 640 px. Moneda más pequeña y separada del importe.
- **Title:** cabeceras de panel compartido; el inspector usa 29 px y peso 500 (28 px móvil).
- **Body:** texto base; los contenidos conservan ajustes locales de 14–15 px.
- **Label:** etiquetas y navegación; metadatos locales de 10–13 px según jerarquía. No son una licencia para reducir texto principal.

**The Dato Rule.** Dinero y métricas usan números tabulares; monospace se reserva a IDs y huellas.

## Layout

Navegación: Operar (Resumen, Facturas, Kauta pregunta, Simulador), Dinero (Wallet, Rendimiento), Control (Proveedores, Reglas, Auditoría, Seguridad). Barra lateral de 232 px a partir de 1024 px; navegación inferior y “Más” en móvil. Ancho de contenido máximo 1280 px; márgenes horizontales de 20/36 px. Escala de espaciado en el frontmatter.

La barra lateral es compacta: enlaces de 42 px, 36 px hasta 850 px de alto y 32 px hasta 700 px de alto, en escritorio. La navegación puede desplazarse en ventanas bajas; esta densidad no cambia el mínimo de los botones compartidos ni la navegación móvil.

Las métricas forman una fila sin tarjetas individuales, con bordes horizontales y separadores verticales. En móvil (hasta 640 px) se organizan en dos columnas; si hay tres métricas, la última ocupa ambas. Resumen combina decisiones e inspector en dos columnas, con separación de 22 px; hasta 1199 px pasan a una columna. El inspector presenta trece columnas de reglas en escritorio y siete hasta 640 px. Facturas usa tabla desde 768 px y lista enlazada debajo.

## Elevation & Depth

Fondos y líneas definen la profundidad ordinaria. La paleta modal añade una sombra difusa (`0 24px 80px -12px #0b173659`) y un fondo de superposición noche translúcido (`#0b173670`). Las transiciones de estado duran 150–160 ms. Se conservan las animaciones existentes de tira, sello y pasos cuando corresponde; reduced-motion reduce duraciones y elimina retrasos.

**The Superficie Rule.** Los paneles ordinarios se separan con fondo y borde, sin sombra decorativa. La búsqueda modal usa sombra para expresar su superposición.

## Shapes

Paneles compartidos e inspector con radio panel; botones compartidos con radio button; tabla y campos con radio table. El radio legacy-panel permanece en contenedores locales anteriores y en el token CSS heredado: no describe el radio efectivo de todos los paneles. Las métricas y los enlaces del recorrido son rectos, separados por líneas. Chips de estado conservan forma de píldora.

## Components

### Buttons

Botones compartidos de al menos 44 px, peso 600 y texto de 12 px; primario azul, secundario blanco con borde, peligro coral, fantasma pizarra y éxito menta oscura. Hover cambia fondo o borde; active desplaza 1 px; deshabilitado reduce opacidad y bloquea la acción. Foco global de 2 px azul, separado 2 px.

### Chips

Estado escrito más punto de color, superficie suave y contorno tenue. Pagada usa menta, Pendiente ámbar, Frenada coral; Rechazada usa neutros y Devuelta por el banco contorno coral sobre blanco.

### Cards / Containers

Paneles blancos con borde bruma, sin sombra decorativa. Cabecera de 22/24/18 px (arriba/horizontal/abajo), 20/18/17 px móvil; cuerpo predeterminado de 20 px. Las métricas comparten una sola superficie abierta. No confundir el nombre interno TarjetasMetricas con tarjetas visuales individuales.

### Inputs / Fields

Campo blanco con borde bruma, altura mínima 40 px, texto de 14 px y placeholder pizarra. Foco cambia borde a azul y añade anillo azul suave. Los formularios conservan etiquetas visibles o accesibles; el placeholder no las reemplaza.

### Navigation

Barra noche con grupos y enlaces compactos; activo en capa oscura, texto blanco, icono menta y pequeña línea menta en el lateral. Móvil ofrece cuatro destinos y Más, con altura de 64 px más el área segura. Buscador accesible desde la barra y mediante Ctrl/⌘K.

### Paleta de comandos

Búsqueda real de secciones y facturas de la API, por ID, proveedor o número, normalizando mayúsculas y acentos. Diálogo nativo modal con título accesible, campo combobox y resultados listbox; flechas recorren, Enter abre y Escape cierra. También cierra el botón o el clic exterior. Si fallan las facturas, informa el error y mantiene la navegación por secciones. No sustituye ese error por datos inventados. Anchura máxima 580 px, alto máximo 70dvh; móvil 77dvh.

### Inspector de 13 reglas

Panel noche que consulta las decisiones guardadas F01, F07, F12 y F10. Selecciona una factura y una regla; muestra nombre, resultado y detalle persistidos por la API, con enlace a la decisión completa. Cumple, Requiere atención y No aplica usan texto e iconos. La selección mantiene borde visible y elevación de 4 px; no simula evaluación. Carga y error con Reintentar tienen estados separados.

### Recepción de correo

Facturas muestra el estado y los documentos de la API de correo del servidor. La conexión y los secretos OAuth permanecen en ese servidor; el navegador no consulta Gmail directamente. Carga, error y recepción vacía se distinguen. Retirar un documento requiere permiso y confirmación; el correo original y el historial financiero se conservan. Una respuesta anterior no debe sobrescribir una consulta más reciente.

### Superficies existentes

- Resumen: una lente por persona con métricas de `/api/resumen`, trabajo pendiente e inspector de decisiones.
- Detalle: monto, motivo, sello y 13 reglas. Recibo con máximo cinco líneas, costos desconocidos como “—”, detalle desplegable, infraestructura provisional.
- Rendimiento: las mismas cuatro métricas para todos, barra de cuatro fuentes y desglose de lectura a un clic. Costos en curso separados del costo por resuelta.
- Seguridad: controles y alcance de demo, sin formularios de contraseñas o TOTP. La identidad se elige sin contraseña y se declara demostración sin autenticación.

Se conserva el contrato de recuperación: un 401 renueva sesión y reintenta una lectura una sola vez; una escritura requiere repetir la acción. Los errores muestran Reintentar, nunca un esqueleto permanente.

## Do's and Don'ts

### Do:
- **Do** conservar la identidad noche, niebla y el semáforo de decisiones.
- **Do** mostrar como máximo cuatro métricas de cabecera, con separadores y sin tarjetas individuales.
- **Do** distinguir carga, vacío y error; ofrecer Reintentar cuando corresponde.
- **Do** mantener foco visible, etiquetas y preferencia de movimiento reducido.
- **Do** validar F01 → F07 → F12 → Rendimiento → CEO/F10 a 390 y 1440 px.

### Don't:
- **Don't** añadir KPIs a los desgloses, gráficas decorativas ni cifras calculadas por la vista.
- **Don't** usar solo color para comunicar estado.
- **Don't** representar las reglas guardadas como una evaluación nueva o una animación de progreso.
- **Don't** extender el radio heredado de 14 px a los paneles compartidos actuales.


Deriva no canonizada: el CSS conserva declaraciones y clases locales de radio 14 px y estilos anteriores sobrescritos por la cascada; no son reglas nuevas del sistema. Este registro se deriva del código terminado y fusiona la documentación vigente; no supone un PRODUCT.md nuevo ni una aprobación de identidad distinta.
