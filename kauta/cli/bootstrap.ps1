# Instala (si hace falta) y arranca la TUI de Kauta en Windows con PowerShell,
# sin necesitar bash ni WSL. Requiere Python 3.11+ y git en el PATH.
#
# Uso:
#   .\bootstrap.ps1 https://tu-kauta.example
#   $env:KAUTA_URL = "https://tu-kauta.example"; .\bootstrap.ps1
#
# Variables opcionales:
#   $env:REPO_DIR  dónde clonar/usar el repo (por defecto: $HOME\hackaton30xBlinka)
#   $env:KAUTA_URL URL base de la API (por defecto: la demo pública)

param(
    [string]$ApiUrl = $(if ($env:KAUTA_URL) { $env:KAUTA_URL } else { "https://kauta.2-25-233-186.sslip.io" })
)

$ErrorActionPreference = "Stop"

function Log($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

$RepoUrl = "https://github.com/FilipaoVfx/hackaton30xBlinka.git"
$RepoDir = if ($env:REPO_DIR) { $env:REPO_DIR } else { Join-Path $HOME "hackaton30xBlinka" }

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "No se encontró Python 3.11+ en el PATH. Instálalo desde https://python.org e inténtalo de nuevo."
    exit 1
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "No se encontró git en el PATH."
    exit 1
}

# 1. Repo: usa el actual si ya estamos parados sobre kauta/cli, clónalo si no.
$cwdPyproject = Join-Path (Get-Location) "pyproject.toml"
if ((Test-Path (Join-Path (Get-Location) "kauta_cli")) -or
    ((Test-Path $cwdPyproject) -and (Select-String -Path $cwdPyproject -Pattern '^name = "kauta-cli"' -Quiet))) {
    $CliDir = (Get-Location).Path
} elseif (Test-Path (Join-Path $RepoDir "kauta\cli")) {
    Log "Repo ya presente en $RepoDir"
    $CliDir = Join-Path $RepoDir "kauta\cli"
} else {
    Log "Clonando $RepoUrl en $RepoDir"
    git clone --depth 1 $RepoUrl $RepoDir
    $CliDir = Join-Path $RepoDir "kauta\cli"
}

Set-Location $CliDir

# 2. Entorno virtual propio del CLI.
$venvPython = Join-Path $CliDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Log "Creando entorno virtual en $CliDir\.venv"
    & $python.Source -m venv .venv
}

$ok = $true
try { & $venvPython -c "import textual, httpx" 2>$null } catch { $ok = $false }
if ($LASTEXITCODE -ne 0) { $ok = $false }
if (-not $ok) {
    Log "Instalando dependencias (textual, httpx)"
    & $venvPython -m pip install -q --upgrade pip
    & $venvPython -m pip install -q -e .
}

# 3. Arrancar.
Log "Conectando a $ApiUrl"
& $venvPython -m kauta_cli.app --url $ApiUrl
