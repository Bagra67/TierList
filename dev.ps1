# Lance le backend FastAPI et le frontend Vite en mode dev dans le même terminal.
# Ctrl+C arrête les deux serveurs.
#
# Usage : .\dev.ps1 [-NoDb] [-NoOpen]   (ou dev.cmd [-NoDb] [-NoOpen] si l'exécution de scripts
# PowerShell est bloquée)
#   -NoDb   : ne démarre pas les services Docker (PostgreSQL, Mailpit, SeaweedFS)
#   -NoOpen : n'ouvre pas les liens de dev dans le navigateur

param(
    [switch]$NoDb,
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'

# Délai maximal d'attente des serveurs avant d'ouvrir le navigateur (premier lancement de Vite compris)
$openBrowserTimeoutSeconds = 60

# Vrai dès qu'un serveur accepte les connexions sur ce port de 127.0.0.1
function Test-PortAcceptsConnections([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', $port)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

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

# La base doit être prête avant le backend : sinon il démarre, mais /health/db échoue
if (-not $NoDb) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "'docker' est introuvable dans le PATH. Voir README.md > Prérequis, ou relancez avec -NoDb." -ForegroundColor Red
        exit 1
    }
    # Via cmd : sous PowerShell 5.1, rediriger le stderr d'un exécutable lève une erreur avec 'Stop'
    cmd /c 'docker info >nul 2>&1'
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Docker ne répond pas : lancez Docker Desktop puis relancez (ou .\dev.ps1 -NoDb pour démarrer sans base).' -ForegroundColor Red
        exit 1
    }
    Write-Host '[db] Démarrage de PostgreSQL, Mailpit et SeaweedFS (docker compose up -d --wait)...' -ForegroundColor Cyan
    docker compose -f (Join-Path $root 'compose.yaml') up -d --wait
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Échec du démarrage des services Docker : voir docker compose logs.' -ForegroundColor Red
        exit 1
    }
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
    if (-not $NoOpen) {
        # Attend que le backend et le frontend répondent (ou qu'un serveur s'arrête), puis ouvre les liens
        $deadline = (Get-Date).AddSeconds($openBrowserTimeoutSeconds)
        while (-not ((Test-PortAcceptsConnections 8000) -and (Test-PortAcceptsConnections 5173))) {
            if (($processes | Where-Object HasExited) -or (Get-Date) -gt $deadline) {
                break
            }
            Start-Sleep -Seconds 1
        }
        if ((Test-PortAcceptsConnections 8000) -and (Test-PortAcceptsConnections 5173)) {
            # localhost et non 127.0.0.1 : même origine que FRONTEND_BASE_URL et l'URI de redirection Google
            Start-Process 'http://localhost:5173'
            Start-Process 'http://127.0.0.1:8000/docs'
            if (-not $NoDb) {
                Start-Process 'http://localhost:8025'
                # Interface web du filer SeaweedFS, ouverte sur le bucket des images
                Start-Process 'http://localhost:8888/buckets/tierlist-images/'
            }
        }
        elseif (-not ($processes | Where-Object HasExited)) {
            Write-Host "Serveurs pas prêts après $openBrowserTimeoutSeconds s : liens non ouverts dans le navigateur." -ForegroundColor Yellow
        }
    }

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
