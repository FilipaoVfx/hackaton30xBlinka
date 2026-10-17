# Estado de Kauta tras el límite de Claude

## Continuación terminada

El 17 de octubre se completaron el selector sin contraseña, la recuperación
401, los errores con reintento, el resumen por rol, el recibo y Rendimiento.
La navegación no necesita scroll a 1440 px de ancho y alturas de 900, 768 y
640 px; las diez secciones se probaron sin recorte horizontal a 390/1440 px.
Se conservan las aserciones existentes y pasan 76 pruebas, incluida una
falla forzada después de crear un pago y sus costos: nada del intento sobrevive.
TypeScript y la compilación también pasan. El recorrido Playwright verifica
F01/F07/F12/F10, dos firmas, permisos, carga XML y recuperación 401/502.

La API está habilitada como `kauta.service`, con un solo proceso, datos fuera
del repo y HTTPS válido en `https://kauta.2-25-233-186.sslip.io`.
La vista de revisión permanece en el túnel compartido con el usuario.
Vercel lo desplegará manualmente el usuario: Root Directory `kauta/web`.
Queda pendiente recibir su URL para autorizar ese origen exacto en la API;
no se declara desplegado en Vercel hasta verificar esa URL.

F10 requiere una preparación opcional y auditada del recorrido: presupuesto
simulado USD 20.000 y primera firma CFO. El set oficial no se modifica.
F12 exige confirmar la fecha de vencimiento antes de aprobar; los XML fiscales
con plazo contractual mantienen la excepción existente. Véase `kauta/README.md`.

Lo siguiente conserva el diagnóstico histórico anterior a la implementación.


Revisión de Codex del 17 de octubre de 2026 sobre `b1ee286`.
Plan: [kauta-finops-rediseno.md](kauta-finops-rediseno.md).

## Punto de continuación

Claude guardó dos commits: `ffbc43a` (importación, tres roles, entrada
por persona y reevaluación) y `b1ee286` (libro de costos y métricas).
Su última ejecución terminó con 71 pruebas aprobadas y una fallida.
`test_personas_invitacion_registro_y_roles` es una función dentro de
`kauta/tests/test_servidor.py`, no un archivo independiente.

El fallo se reprodujo: `POST /api/personas/invitar` devolvía 409 porque el
usuario de prueba ya existía. `test_costos.py` importaba la configuración
durante la recolección, antes de que `test_servidor.py` definiera la base
temporal. La suite completa usaba la base local `kauta/var/kauta.db`.

La corrección local mueve la configuración temporal a `tests/conftest.py`,
que pytest carga antes de recolectar los módulos. La conexión se cierra y
la carpeta temporal se elimina al terminar la sesión. Una prueba nueva
verifica que tanto CONFIG como el motor SQL usan esa carpeta. No se
eliminaron ni relajaron aserciones existentes.

Validación: 73 pruebas aprobadas; `npm run typecheck` y `npm run build`
aprobados. Las pruebas con TestClient requieren ejecutarse fuera del
sandbox de esta sesión, donde se bloqueaban.

## Estado frente al plan

| Bloque | Estado observado |
| --- | --- |
| T1 · importación | Código en git; no se repitió la auditoría de secretos ni el clon limpio |
| T2 · roles y semilla | Tres roles implementados; falta el cierre del guion con F10 |
| T3 · persona y reentrada | Endpoint de persona probado; falta recuperación 401 en el cliente |
| T4 · vencimiento R01 | Implementado; suite del set aprobada |
| T5 · reevaluación | Implementado y cubierto por pruebas |
| T6–T8 · costos, métricas y semilla | Implementados; pruebas de aceptación, conciliación, IA ×10 y restablecimiento aprobadas |
| T9 · frontend sin login y errores | Pendiente: App aún importa Login y Personas; falta EstadoCarga y reintentos |
| T10 · rediseño y vistas | Pendiente: Resumen ignora `lente`; no existe Rendimiento ni el recibo en Detalle; falta DESIGN.md |
| T11 · orígenes | Existe KAUTA_ORIGEN; falta verificar el origen público definitivo |
| T12 · despliegue | Pendiente: no están los archivos ops de Kauta ni web/vercel.json |
| T13 · recorrido web | Pendiente: el script todavía busca “Jurado Hackathon 30X”, eliminado de la semilla |

## Hallazgos que condicionan la continuación

1. **F10 no está preparada para el cierre de la demo.** El plan dice que
   debe traer una firma del CFO; la semilla no la crea. Además,
   `test_regla_dura_no_se_salta_aprobando` comprueba que aprobar F10 devuelve
   409 por R12. Hay que preparar una situación de demo válida y probarla,
   conservando el bloqueo de las reglas duras.
2. **El plan contiene decisiones antiguas y nuevas.** La sección 6 elimina
   invitación y gestión de usuarios, pero D8 conserva ese flujo por API y
   exige mantener sus aserciones. La implementación actual sigue D8;
   quitar la pantalla Personas no exige borrar la API ni sus pruebas.
3. **El despliegue también cambió durante la revisión.** El cambio tardío
   menciona FastAPI en Vercel, pero D6 decide API y SQLite en este servidor,
   con frontend Vercel y proxy del mismo origen. Esa decisión posterior
   debe guiar T12. D9 difiere `as_of` y D15 difiere GitHub Actions a un TODO.
4. **La suite verde no valida la interfaz pendiente.** Compilar el frontend
   actual no demuestra selector, recibo, lentes, 401/502 ni el recorrido de
   dos minutos a 390 y 1440 px.

El siguiente bloque de implementación es T9–T10, acompañado por el ajuste
del guion de F10 y T13. Después corresponde T11–T12 y verificar la URL final.
Los cambios locales previos en prototipos y README se conservaron.
