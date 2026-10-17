"""Ejecuta el recorrido Playwright de Kauta (requiere npm ci en web/).

Uso: KAUTA_URL=http://127.0.0.1:8840 python scripts/probar_web.py [salida]
Primera instalación de Chromium: cd web && npx playwright install chromium
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).with_suffix(".mjs")
    raise SystemExit(subprocess.call(["node", str(script), *sys.argv[1:]]))
