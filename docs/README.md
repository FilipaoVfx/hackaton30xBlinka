# Documentación de Kauta

Kauta es un agente de cuentas por pagar de demostración (datos ficticios, sin dinero real). Esta carpeta reúne las páginas y diagramas de lo que Kauta tiene hoy; la fuente de las afirmaciones técnicas es `aidlc-docs/inception/hechos-del-codigo.md`.

## Quiero entender / Documento
| Quiero entender | Documento |
|---|---|
| Qué es Kauta, qué la distingue y qué no hace | [`propuesta.html`](propuesta.html) |
| Cómo está construida (C4, objetivo frente a hoy, seguridad, costos) | [`arquitectura.html`](arquitectura.html) |
| Quién puede hacer qué y el recorrido F01, F07, F12, F10 | [`personas.html`](personas.html) |
| Las tablas y sus relaciones | [`modelo-de-datos.html`](modelo-de-datos.html) |
| Los hechos del código con evidencia ruta:línea | [`../aidlc-docs/inception/hechos-del-codigo.md`](../aidlc-docs/inception/hechos-del-codigo.md) |
| Cómo arrancar y probar la aplicación | [`../kauta/README.md`](../kauta/README.md) |
| El sistema de interfaz | [`../kauta/DESIGN.md`](../kauta/DESIGN.md) |
| El diseño del rediseño FinOps y el estado del 2026-10-17 | [`designs/kauta-finops-rediseno.md`](designs/kauta-finops-rediseno.md), [`designs/kauta-estado-2026-10-17.md`](designs/kauta-estado-2026-10-17.md) |
| Pendientes registrados | [`../TODOS.md`](../TODOS.md) |

## Diagramas (`c4/`)
Cada diagrama tiene fuente Mermaid (`.mmd`), `.svg` y `.png`: `c1-contexto`, `c2-contenedores`, `c3-motor`, `c3-servidor`, `c3-web`, `d1-flujo-factura`, `p1-personas`, `p2-recorridos`. Se regeneran con `mmdc -i <archivo>.mmd -o <archivo>.png -s 2 -b white`.

## Aviso
`PRD.md` es un borrador anterior; donde se contradiga con el código, manda la ficha de hechos. Los HTML son autónomos: se abren con doble clic.
