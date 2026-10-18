# Kauta CLI

Otra forma de consumir la misma API de Kauta (la que ya usa `web/`): una TUI de
terminal estilo `k9s`, pensada para una demo rápida — paneles vivos, navegación
por teclado, sin sacrificar performance por efectos cosméticos. No reemplaza al
frontend; es un cliente HTTP adicional de solo esa misma API pública.

## Arrancar en un paso (cualquier máquina)

- **Linux/macOS/WSL (bash):**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/FilipaoVfx/hackaton30xBlinka/main/kauta/cli/bootstrap.sh | bash -s -- https://tu-kauta.example
  ```
- **Windows (PowerShell, sin WSL):**
  ```powershell
  iwr -useb https://raw.githubusercontent.com/FilipaoVfx/hackaton30xBlinka/main/kauta/cli/bootstrap.ps1 -OutFile bootstrap.ps1
  .\bootstrap.ps1 https://tu-kauta.example
  ```

Ambos scripts: clonan el repo si hace falta, crean su propio `.venv`, instalan
`textual`/`httpx` solo la primera vez, y arrancan la TUI apuntando a la URL dada
(por defecto `http://127.0.0.1:8000`, o la variable `KAUTA_URL`).

## Arrancar manualmente

1. Backend (desde `kauta/`, modo demo):

   ```bash
   uvicorn servidor.main:app --host 127.0.0.1 --port 8000
   ```

2. CLI (desde `kauta/cli/`, en su propio entorno):

   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e .
   kauta --url http://127.0.0.1:8000
   # o, sin instalar: python -m kauta_cli.app --url http://127.0.0.1:8000
   ```

   La URL también puede venir de la variable `KAUTA_URL` (por defecto
   `http://127.0.0.1:8000`).

## Navegación

| Tecla | Acción |
|---|---|
| `1`–`6` | Resumen / Facturas / Wallet / Pagos / Auditoría / Simulador |
| `p` | Cambiar de persona (demo, sin contraseña) |
| `r` | Refrescar la pantalla actual |
| `a` / `x` | En Facturas: aprobar / rechazar la factura seleccionada |
| `f` | En Wallet: fondear la cuenta operativa |
| `t` | En Pagos: reintentar un pago devuelto |
| `a` | En Simulador: simular un año completo contra el motor de 13 reglas |
| `q` | Salir |

## Diseño (por qué está hecho así)

- **Un solo `httpx.AsyncClient`** para toda la sesión — nunca se abre una conexión
  nueva por request (`kauta_cli/client.py`).
- **Auth igual que el frontend**: cookie de sesión `HttpOnly` + token CSRF
  sincronizado en `X-CSRF-Token` para todo método que cambia datos (ver
  `servidor/seguridad/sesiones.py`).
- **Refresco según volatilidad real de cada dato**, no un único polling global:
  Resumen cada 2.5s, Auditoría cada 1s (solo agrega eventos nuevos, nunca
  reconstruye el log), Facturas/Wallet/Pagos on-demand + `r` manual.
- **El simulador de año** (`/api/simulador/anio`) corre en memoria en el
  servidor; la pantalla 6 revela el resultado real con un conteo animado — la
  animación es solo una forma de mostrar el número final, nunca un dato
  inventado a mitad de camino.

## Pruebas

Con el backend corriendo, se puede ejercitar toda la TUI sin terminal real usando
el modo headless de Textual (`App.run_test()` / `Pilot`), simulando teclas y
leyendo el árbol de widgets — así se validó el recorrido completo (login,
las 6 pantallas, aprobar/rechazar, fondear wallet, simular un año, cambiar de
persona) antes de esta entrega.
