# Lance le backend FastAPI et le frontend Vite en mode dev dans le même terminal.
# Ctrl+C arrête les deux serveurs.
#
# Usage : .\dev.ps1   (ou dev.cmd si l'exécution de scripts PowerShell est bloquée)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'

# Un venv activé ailleurs (ex : terminal VS Code) ferait ignorer backend/.venv par uv
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue

foreach ($tool in 'uv', 'pnpm') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "'$tool' est introuvable dans le PATH. Voir README.md > Prérequis." -ForegroundColor Red
        exit 1
    }
}

# Installation automatique au premier lancement (après un clone)
if (-not (Test-Path (Join-Path $backendDir '.venv'))) {
    Write-Host '[backend] Installation des dépendances (uv sync)...' -ForegroundColor Cyan
    uv sync --directory $backendDir
}
if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Write-Host '[frontend] Installation des dépendances (pnpm install)...' -ForegroundColor Cyan
    pnpm --dir $frontendDir install
}

Write-Host ''
Write-Host '  Backend  : http://127.0.0.1:8000  (docs : http://127.0.0.1:8000/docs)' -ForegroundColor Green
Write-Host '  Frontend : http://localhost:5173' -ForegroundColor Green
Write-Host '  Ctrl+C pour tout arrêter' -ForegroundColor Yellow
Write-Host ''

# cmd /c résout uv.exe et pnpm.cmd ; -NoNewWindow partage la console, donc Ctrl+C atteint les deux
$processes = @(
    Start-Process cmd.exe -ArgumentList '/c', 'uv run fastapi dev app/main.py --port 8000' `
        -WorkingDirectory $backendDir -NoNewWindow -PassThru
    Start-Process cmd.exe -ArgumentList '/c', 'pnpm dev --port 5173 --strictPort' `
        -WorkingDirectory $frontendDir -NoNewWindow -PassThru
)

try {
    # Si l'un des deux serveurs s'arrête (erreur, port occupé...), on arrête l'autre
    while (-not ($processes | Where-Object HasExited)) {
        Start-Sleep -Milliseconds 500
    }
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) {
            # /T : arrête aussi les processus enfants (python, node)
            taskkill /PID $process.Id /T /F *> $null
        }
    }
    Write-Host ''
    Write-Host 'Serveurs arrêtés.' -ForegroundColor Yellow
}
