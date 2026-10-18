---
name: "Kauta"
description: "Operación financiera con decisiones y evidencia verificable."
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
  rail-label: "#becae2"
  rule-pass-bg: "#164438"
  rule-pass-text: "#90ebd4"
  metric-line: "#d4dcea"
typography:
  headline:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "32px"
    fontWeight: 800
    lineHeight: "1.2"
    letterSpacing: "-.035em"
  inspector-title:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: "1.15"
    letterSpacing: "-.035em"
  metric:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "28px"
    fontWeight: 800
    lineHeight: "1.3"
    letterSpacing: "-.035em"
  title:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 800
    letterSpacing: "-.02em"
  body:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "1.5"
  button:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 750
    lineHeight: "1.4"
  label:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "11px"
    fontWeight: 650
  rail-label:
    fontFamily: "Manrope Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "9px"
    fontWeight: 650
rounded:
  cell: "6px"
  tab: "9px"
  button: "10px"
  navigation: "12px"
  panel: "14px"
  modal: "16px"
spacing:
  step-4: "4px"
  step-8: "8px"
  step-12: "12px"
  step-16: "16px"
  step-20: "20px"
  step-24: "24px"
  step-28: "28px"
  step-32: "32px"
  step-38: "38px"
  step-48: "48px"
components:
  button-primary:
    textColor: "{colors.panel}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
    backgroundColor: "{colors.azul}"
  button-secondary:
    textColor: "{colors.noche}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
    backgroundColor: "{colors.panel}"
  button-success:
    textColor: "{colors.panel}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
    backgroundColor: "{colors.menta-t}"
  button-danger:
    textColor: "{colors.coral-t}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
    backgroundColor: "{colors.coral-s}"
  button-ghost:
    textColor: "{colors.pizarra}"
    typography: "{typography.button}"
    rounded: "{rounded.button}"
    padding: "11px 17px"
  button-primary-hover:
    backgroundColor: "{colors.azul-t}"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.noche}"
    rounded: "{rounded.panel}"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.noche}"
    rounded: "{rounded.button}"
    padding: "8px 12px"
  chip-paid:
    backgroundColor: "{colors.menta-s}"
    textColor: "{colors.menta-t}"
    rounded: "{rounded.cell}"
    padding: "5px 8px"
---

# Design System: Kauta

## Overview

**Creative North Star: "El desplegable financiero"**

Kauta traduce el orden de un informe anual corporativo a una herramienta de trabajo: envolvente noche, Manrope firme, superficies claras y grupos amplios de información. Alineación y líneas finas organizan la densidad; la evidencia de una decisión recibe el mayor contraste.

La paleta principal permanece y la composición anterior se reemplaza. Los controles convencionales de HeroUI permiten operar; la firma visual es una matriz de reglas con nombre, estado y motivo verificable. La marca usa el SVG existente y la tipografía se sirve localmente; no se incorporan imágenes rasterizadas.

**Key Characteristics:**

- Envolvente noche y rail estrecho.
- Manrope local y cifras tabulares.
- Superficies planas delimitadas por líneas.
- Evidencia interactiva y demo identificada.

## Colors

La estructura noche y las superficies frías claras sostienen señales financieras saturadas. Los valores canónicos están en el frontmatter.

### Primary

Noche sostiene la envolvente y el texto principal. Azul identifica acciones, sección y foco; azul-t oscurece la acción y azul-s señala selección suave.

### Secondary

Menta, ámbar y coral conservan el semáforo. Sus variantes -t y -s resuelven texto y superficie sobre blanco. Rule-pass-bg y rule-pass-text adaptan el resultado favorable al inspector oscuro; fallos usan ámbar o coral con texto noche.

### Neutral

Panel es blanco; niebla, el lienzo; pizarra, el texto secundario; bruma y metric-line, los divisores. Noche-2 y noche-3 distinguen controles oscuros; rail-label mantiene visibles sus etiquetas.

**The Semáforo Rule.** Menta identifica un resultado favorable, ámbar una escalación y coral un freno. Cada estado lleva texto o icono además de color; azul identifica acción y foco.

## Typography

**Display Font / Body Font:** Manrope Variable local con la pila sans del frontmatter. **Label/Mono Font:** la misma Manrope para etiquetas; ui-monospace, SFMono-Regular, Cascadia Mono, Menlo, Consolas, monospace para IDs y huellas.

La familia única une títulos institucionales y controles compactos. Los pesos altos distinguen importes y decisiones sin añadir otra voz.

- **Headline:** cabecera compartida; 29 px hasta 767 px, frente al token de escritorio.
- **Inspector title:** dos líneas; 27 px en móvil, peso 700.
- **Metric:** importes; 25 px hasta 1250 px y 26 px hasta 767 px, con moneda separada de 10 px.
- **Title:** cabeceras de panel, 16 px y peso 800.
- **Body:** base de 14 px; descripción de página de 13 px, interlínea 1.7 y máximo 65ch, 12 px móvil.
- **Button / Label:** acciones de 12 px y etiquetas operativas de 10–12 px. La etiqueta específica de rail de 9 px lleva icono y tooltip; no trasladarla al texto de trabajo.

**The Dato Rule.** Importes y métricas usan cifras tabulares; la pila mono se reserva a identificadores y huellas.

## Layout

A 1440 px, rail fijo noche de 88 px y barra global de 80 px. El contenido tiene máximo de 1520 px, margen automático y padding de 36 px arriba, 38 px horizontal y 48 px abajo. La barra de contexto y el pie siguen el mismo eje.

El Resumen terminado sitúa cabecera con acción, inspector a la izquierda y cola humana a la derecha en proporción 1.3:1 y separación de 24 px. La tira financiera va debajo. Cuatro métricas comparten bordes horizontales y divisores verticales; no son tarjetas independientes. El recorrido de demo cierra la superficie.

Las trece reglas tienen siete columnas iguales y separación de 7 px. Cada celda muestra ID, nombre y señal. Hasta 767 px usan tres columnas con separación de 8 px; inspector y cola pasan a una columna.

Hasta 1023 px desaparece el rail y aparece navegación inferior con cuatro secciones y Más, altura mínima de 64 px más área segura. A 390 px, barra global de 68 px, contexto con padding 14/20 px y contenido con padding 25/20/100 px. Métricas en dos columnas; la tercera, cuando existe, ocupa ambas. Facturas usa tabla desde 768 px y lista debajo. El recorrido usa una columna, dos desde 640 px y cuatro desde 1280 px.

En escritorio bajo se compactan marca y enlaces a alturas de ventana de 760 y 640 px; por debajo de 540 px el rail admite desplazamiento. La escala combina pasos de 4 px con márgenes estructurales observados de 38 px.

## Elevation & Depth

Fondos y líneas definen profundidad ordinaria. Paneles sin sombra. Diálogo compartido: `0 24px 70px -18px #0b17365c`, backdrop `#0b1736a6`. Búsqueda modal: `0 24px 80px -12px #0b173659`, backdrop `#0b173670`. Avisos flotantes: `0 10px 30px -10px rgba(11,23,54,.5)`.

Transiciones de fondo/color de 160 ms; fila de decisión de 150 ms; celda de 180 ms. Selección de regla sube 4 px y añade borde blanco. Reduced-motion reduce animaciones y transiciones a .01 ms y elimina retrasos. La tira puede entrar con encender de 240 ms; no representa evaluación nueva.

**The Superficie Rule.** Los paneles ordinarios se separan con fondo y borde, sin sombra decorativa; las sombras expresan superposición en diálogos y avisos.

## Shapes

Paneles e inspector con esquinas de 14 px; botones y campos de 10 px; navegación del rail de 12 px; diálogos de 16 px. Chips y celdas de 6 px. Tabla y paleta de comandos de 12 px. Avatares y puntos circulares. Métricas abiertas y rectas. El sello conserva borde y leve rotación.

## Components

### Buttons

HeroUI Button: mínimo de 44 px, padding 11/17 px, radio button y tipografía button. Primario azul; secundario blanco con borde interior; éxito menta-t; peligro coral-s; fantasma transparente. Hover del primario azul-t; secundario niebla; éxito verde más oscuro; fantasma superficie neutra. Disabled reduce opacidad a .5 y bloquea interacción. Foco global de 2 px azul separado 3 px; campos tienen tratamiento propio.

### Chips

HeroUI Chip con estado escrito y punto. Pagada menta-s/menta-t; Pendiente ámbar-s/ámbar-t; Frenada coral-s/coral-t; Rechazada neutros; Devuelta por el banco coral sobre blanco. Radio de 6 px, padding 5/8 px, texto de 10 px y mínimo de 24 px.

### Cards / Containers

Blanco, borde bruma, radio panel y sin sombra. Cabecera de 22/24 px y cuerpo predeterminado de 20 px. En móvil, cabecera de 20/18 px. Filas de decisión enlazadas con divisores y hover niebla.

### Inputs / Fields

Blanco, borde bruma, radio button, padding 8/12 px y mínimo de 40 px. Texto de 14 px y placeholder pizarra. Foco: borde azul y anillo azul al 20%. La etiqueta visible o accesible acompaña al campo.

### Navigation

Rail con icono lineal y etiqueta; enlace de 68/53 px, hover noche-3 y activo menta con texto noche. HeroUI Tooltip da nombre completo. Persona en rail y barra global. Móvil: destino activo azul, Más abre otras secciones. Ctrl/⌘K abre búsqueda de secciones y facturas.

### Inspector de reglas

Panel noche con HeroUI Tabs para F01, F07, F12 y F10. Trece botones nombrados con aria-pressed y señal además de color. Selección revela detalle de API y enlace a decisión completa. Tabs activos blancos sobre noche-2. Carga y error con Reintentar se distinguen.

### Diálogos y búsqueda

HeroUI Modal con título, cierre, divisor de cabecera y cuerpo desplazable de 24 px (20 px móvil). Paleta de comandos: diálogo nativo, combobox y listbox; máximo de 580 px y 70dvh (78dvh móvil). Flechas recorren, Enter abre y Escape cierra.

## Do's and Don'ts

### Do:

- **Do** conservar la paleta principal y los significados del semáforo.
- **Do** mantener nombres legibles en las trece reglas y revelar el motivo al seleccionarlas.
- **Do** conservar foco visible, navegación por teclado y preferencia de movimiento reducido.
- **Do** distinguir carga, vacío y error, con Reintentar cuando corresponde.
- **Do** revisar a 1440 px y 390 px, incluidas personas y Facturas.

### Don't:

- **Don't** comunicar estado solo con color.
- **Don't** presentar decisiones guardadas como una evaluación nueva o un progreso ficticio.
- **Don't** recuperar la barra lateral de 232 px ni las tarjetas iguales de la interfaz sustituida.
- **Don't** inventar cifras, resultados ni evidencia visual de Gmail conectado.

Deriva no canonizada: ninguna infracción material identificada por la revisión final. Este registro procede del código terminado; no promueve las reglas Inter ni el rail de 232 px del sistema sustituido.
