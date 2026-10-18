#!/usr/bin/env bash
# Instala (si hace falta) y arranca la TUI de Kauta en cualquier máquina con
# Python 3.11+ y git. No toca el backend: solo apunta a una URL de la API.
#
# Uso:
#   ./bootstrap.sh [URL_DE_LA_API]
#   KAUTA_URL=https://mi-kauta.example ./bootstrap.sh
#
# Variables opcionales:
#   REPO_DIR   dónde clonar/usar el repo (por defecto: ~/hackaton30xBlinka)
#   KAUTA_URL  URL base de la API (por defecto: la demo pública)
set -euo pipefail

REPO_URL="https://github.com/FilipaoVfx/hackaton30xBlinka.git"
REPO_DIR="${REPO_DIR:-$HOME/hackaton30xBlinka}"
API_URL="${1:-${KAUTA_URL:-https://kauta.2-25-233-186.sslip.io}}"

log() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }

command -v python3 >/dev/null || { echo "Falta python3 (3.11+)." >&2; exit 1; }
command -v git >/dev/null || { echo "Falta git." >&2; exit 1; }

# 1. Repo: usa el actual si ya estamos parados sobre él, clónalo si no existe.
if [ -d "$(pwd)/kauta_cli" ] || [ -f "$(pwd)/pyproject.toml" ] && grep -q "^name = \"kauta-cli\"" "$(pwd)/pyproject.toml" 2>/dev/null; then
    CLI_DIR="$(pwd)"
elif [ -d "$REPO_DIR/kauta/cli" ]; then
    log "Repo ya presente en $REPO_DIR"
    CLI_DIR="$REPO_DIR/kauta/cli"
else
    log "Clonando $REPO_URL en $REPO_DIR"
    git clone --depth 1 "$REPO_URL" "$REPO_DIR"
    CLI_DIR="$REPO_DIR/kauta/cli"
fi

cd "$CLI_DIR"

# 2. Entorno virtual propio del CLI (no se mezcla con el del backend).
if [ ! -d ".venv" ]; then
    log "Creando entorno virtual en $CLI_DIR/.venv"
    python3 -m venv .venv
fi
# shellcheck source=/dev/null
. .venv/bin/activate

if ! python -c "import textual, httpx" >/dev/null 2>&1; then
    log "Instalando dependencias (textual, httpx)"
    pip install -q --upgrade pip
    pip install -q -e .
fi

# 3. Arrancar.
log "Conectando a $API_URL"
exec python -m kauta_cli.app --url "$API_URL"
