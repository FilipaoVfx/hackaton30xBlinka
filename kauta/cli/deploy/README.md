# Terminal web de la TUI (cero instalación para el jurado)

Para que cualquier persona abra la TUI de Kauta desde su propio navegador —sin
Python, sin git, sin PowerShell— sin instalar nada: `ttyd` sirve la TUI por
WebSocket y un túnel rápido de Cloudflare la publica con HTTPS. Mismo patrón que
ya se usa en este VPS para otros monitores (`monitores-tunnel.service`,
`cryptoreport-urania-tunnel.service`).

```
navegador (jurado) → https://*.trycloudflare.com → cloudflared → ttyd (127.0.0.1:8742)
                                                                     └─ spawnea una TUI por cada pestaña
                                                                        → kauta backend (127.0.0.1:8840, kauta.service)
```

Cada conexión abre su **propio proceso** de la TUI (ttyd no comparte el pty entre
clientes), así que varias personas pueden entrar a la vez sin pelearse por el
cursor — eso sí, todas comparten los mismos datos del backend de demo.

## Instalar (una sola vez)

```bash
apt-get install -y ttyd   # ya viene en Ubuntu/Debian
cp kauta-cli-web.service kauta-cli-tunnel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now kauta-cli-web.service kauta-cli-tunnel.service
```

## Obtener el link público

La URL de `trycloudflare.com` es aleatoria y **cambia cada vez que se reinicia
`kauta-cli-tunnel.service`** (por eso ese servicio no depende de
`kauta-cli-web.service` con `Requires=`: reiniciar uno no debe tirar el link del
otro). Para verla:

```bash
journalctl -u kauta-cli-tunnel | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1
```

## Seguridad

- `ttyd` solo escucha en `127.0.0.1:8742`; la única puerta de entrada pública es
  el túnel de Cloudflare.
- El comando que ejecuta está fijo en el `ExecStart` (no es un shell): quien
  entra por el link solo puede operar la TUI de Kauta, nunca llegar a bash.
- `-m 25` limita a 25 sesiones concurrentes (una por pestaña/persona) como
  freno simple contra abuso.
- Es el mismo backend de demo que usan los demás clientes (puerto 8840,
  `kauta.service`, `KAUTA_MODO=demo`): las acciones desde la TUI (aprobar
  facturas, fondear wallet, simular un año) afectan ese estado compartido.

## Apagar cuando ya no haga falta

```bash
systemctl disable --now kauta-cli-web.service kauta-cli-tunnel.service
```
