# Kauta · Sistema de interfaz

Kauta es una herramienta para operar cuentas por pagar. La pregunta de cada
pantalla manda sobre la cantidad de datos: como máximo cuatro métricas de
cabecera; los detalles se abren cuando hacen falta.

## Identidad

- Modo claro; barra lateral noche (#0b1736), superficie niebla (#f5f7fb), panel blanco.
- Texto principal noche; secundario pizarra (#5b6782); separadores bruma (#e3e8f2).
- Semáforo reservado a decisiones: menta pagar, ámbar preguntar, coral frenar.
- Azul (#3b5bfd) para acciones y selección. Nunca usar solo color para informar estado.
- Inter Variable local; números tabulares en dinero y métricas; monospace solo para IDs y huellas.

## Estructura

Navegación: Operar (Resumen, Facturas, Kauta pregunta, Simulador), Dinero
(Wallet, Rendimiento), Control (Proveedores, Reglas, Auditoría, Seguridad).
Barra lateral de 232 px a partir de 1024 px; navegación inferior y “Más” en
móvil. Ancho de contenido máximo 1280 px; márgenes de 20/36 px. Escala de
espaciado: 4, 8, 12, 16, 20, 24, 32 px.

Títulos 26–30 px; texto 14–15 px; etiquetas 12–13 px; métricas 25–28 px.
Paneles de radio 14 px, sin sombra decorativa. Las métricas forman una fila
con separadores; en móvil se organizan en dos columnas. No añadir KPIs a
los desgloses. No hay gráficas decorativas ni cifras calculadas por la vista.

## Superficies

- Resumen: una lente por persona, con las tarjetas de `/api/resumen` y trabajo pendiente.
- Detalle: monto, motivo, sello y 13 reglas. Recibo con un máximo de cinco líneas,
  costos desconocidos como “—”, detalle desplegable, infraestructura provisional.
- Rendimiento: mismas cuatro tarjetas para todos, barra de cuatro fuentes,
  desglose de lectura a un clic. Costos en curso separados del costo por resuelta.
- Seguridad: controles y alcance de la demo; sin formularios de contraseñas o TOTP.

## Interacción y accesibilidad

Botones primarios y navegación móvil de al menos 44 px de alto. Foco visible,
etiquetas de formulario, diálogo con título y cierre por Escape. La identidad
se elige sin contraseña; se declara que es demostración sin autenticación.
Un 401 renueva sesión y reintenta una lectura una sola vez; una escritura
requiere repetir la acción. Los errores muestran “Reintentar”, nunca un
esqueleto permanente. Carga, vacío y error se distinguen. Respetar reduced-motion.

Validar el recorrido F01 → F07 → F12 → Rendimiento → CEO/F10 a 390 y 1440 px.
