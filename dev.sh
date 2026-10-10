#!/usr/bin/env bash
# Lance le backend FastAPI et le frontend Vite en mode dev dans le même terminal.
# Ctrl+C arrête les deux serveurs.
#
# Usage (Git Bash, macOS, Linux) : ./dev.sh [--no-db] [--no-open]
#   --no-db   : ne démarre pas la base PostgreSQL (Docker)
#   --no-open : n'ouvre pas les liens de dev dans le navigateur
# Sous PowerShell / cmd, utilisez plutôt dev.cmd.

set -euo pipefail

cd "$(dirname "$0")"

start_db=true
open_browser=true
for arg in "$@"; do
  case "$arg" in
    --no-db) start_db=false ;;
    --no-open) open_browser=false ;;
    -h | --help)
      echo "Usage : ./dev.sh [--no-db] [--no-open]"
      exit 0
      ;;
    *)
      echo "Option inconnue : $arg (usage : ./dev.sh [--no-db] [--no-open])" >&2
      exit 1
      ;;
  esac
done

BACKEND_PORT=8000
FRONTEND_PORT=5173
MAILPIT_PORT=8025
# Délai maximal d'attente des serveurs avant d'ouvrir le navigateur (premier lancement de Vite compris)
OPEN_BROWSER_TIMEOUT_SECONDS=60

# Un venv activé ailleurs (ex : terminal VS Code) ferait ignorer backend/.venv par uv
unset VIRTUAL_ENV
# Sous Windows, Python encode sa sortie en cp1252 quand elle passe par un pipe (emojis -> "??")
export PYTHONUTF8=1

is_windows() {
  command -v taskkill > /dev/null 2>&1
}

# Affiche les PID (Windows) qui écoutent sur un port TCP local.
# Colonne "adresse distante" en :0 = socket en écoute (indépendant de la langue de Windows).
# Pas de "-p TCP" : il masquerait l'IPv6, or Vite écoute sur localhost = [::1].
windows_pids_on_port() {
  netstat -ano | awk -v port=":$1" '
    $1 == "TCP" && $2 ~ port"$" && $3 ~ /:0$/ { print $5 }
  ' | sort -u
}

# Vrai dès qu'un serveur accepte les connexions sur ce port de 127.0.0.1 (redirection /dev/tcp de bash)
port_accepts_connections() {
  (: < "/dev/tcp/127.0.0.1/$1") 2> /dev/null
}

# Ouvre une adresse dans le navigateur par défaut du système
open_url() {
  if is_windows; then
    # explorer.exe rend la main sans attendre, mais renvoie un code non nul même en cas de succès
    explorer.exe "$1" || true
  elif command -v open > /dev/null 2>&1; then
    open "$1"
  elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open "$1" > /dev/null 2>&1
  else
    echo "Aucun navigateur trouvé (open, xdg-open) : ouvrez $1 vous-même." >&2
  fi
}

# Attend que le backend et le frontend répondent, puis ouvre les liens de dev
open_dev_links_when_ready() {
  local waited_seconds=0
  until port_accepts_connections "$BACKEND_PORT" && port_accepts_connections "$FRONTEND_PORT"; do
    if ((waited_seconds >= OPEN_BROWSER_TIMEOUT_SECONDS)); then
      echo "Serveurs pas prêts après ${OPEN_BROWSER_TIMEOUT_SECONDS} s : liens non ouverts dans le navigateur." >&2
      return
    fi
    sleep 1
    waited_seconds=$((waited_seconds + 1))
  done
  # localhost et non 127.0.0.1 : même origine que FRONTEND_BASE_URL et l'URI de redirection Google
  open_url "http://localhost:$FRONTEND_PORT"
  open_url "http://127.0.0.1:$BACKEND_PORT/docs"
  if $start_db; then
    open_url "http://localhost:$MAILPIT_PORT"
  fi
}

port_in_use() {
  if is_windows; then
    [[ -n "$(windows_pids_on_port "$1")" ]]
  elif command -v lsof > /dev/null 2>&1; then
    lsof -iTCP:"$1" -sTCP:LISTEN > /dev/null 2>&1
  else
    return 1
  fi
}

for tool in uv pnpm; do
  if ! command -v "$tool" > /dev/null 2>&1; then
    echo "'$tool' est introuvable dans le PATH. Voir README.md > Prérequis." >&2
    exit 1
  fi
done

# Vérifié avant le démarrage : le nettoyage par port ne doit jamais tuer un processus étranger
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if port_in_use "$port"; then
    echo "Le port $port est déjà utilisé : arrêtez l'application qui l'occupe puis relancez." >&2
    exit 1
  fi
done

# Installation automatique au premier lancement (après un clone)
if [[ ! -d backend/.venv ]]; then
  echo "[backend] Installation des dépendances (uv sync)..."
  (cd backend && uv sync)
fi
if [[ ! -d frontend/node_modules ]]; then
  echo "[frontend] Installation des dépendances (pnpm install)..."
  (cd frontend && pnpm install)
fi

# La base doit être prête avant le backend : sinon il démarre, mais /health/db échoue
if $start_db; then
  if ! command -v docker > /dev/null 2>&1; then
    echo "'docker' est introuvable dans le PATH. Voir README.md > Prérequis, ou relancez avec --no-db." >&2
    exit 1
  fi
  if ! docker info > /dev/null 2>&1; then
    echo "Docker ne répond pas : lancez Docker Desktop puis relancez (ou ./dev.sh --no-db pour démarrer sans base)." >&2
    exit 1
  fi
  echo "[db] Démarrage de PostgreSQL (docker compose up -d --wait)..."
  docker compose up -d --wait
fi

# Préfixe chaque ligne de log par le nom du serveur, en couleur
prefix() {
  local label=$1 color=$2
  sed -u "s/^/$(printf '\033[%sm[%s]\033[0m ' "$color" "$label")/"
}

pids=()
# À part de pids : ce n'est pas un serveur, sa fin ne doit pas tout arrêter (wait -n plus bas)
opener_pid=""

cleanup() {
  trap - INT TERM EXIT
  echo
  echo "Arrêt des serveurs..."
  if [[ -n "$opener_pid" ]]; then
    kill "$opener_pid" 2> /dev/null || true
  fi
  for pid in "${pids[@]}"; do
    if is_windows; then
      # /T : arrête aussi les processus enfants (python, node)
      local winpid
      winpid=$(cat "/proc/$pid/winpid" 2> /dev/null || true)
      [[ -n "$winpid" ]] && taskkill //PID "$winpid" //T //F > /dev/null 2>&1 || true
    fi
    kill "$pid" 2> /dev/null || true
  done
  # Filet de sécurité : sous Git Bash, Ctrl+C peut tuer un parent avant ses enfants
  # (ex : le worker uvicorn), qui garderait alors le port ouvert
  if is_windows; then
    for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
      for winpid in $(windows_pids_on_port "$port"); do
        taskkill //PID "$winpid" //T //F > /dev/null 2>&1 || true
      done
    done
  fi
  wait 2> /dev/null || true
  echo "Serveurs arrêtés."
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo
echo "  Backend  : http://127.0.0.1:$BACKEND_PORT  (docs : http://127.0.0.1:$BACKEND_PORT/docs)"
echo "  Frontend : http://localhost:$FRONTEND_PORT"
echo "  Ctrl+C pour tout arrêter"
echo

(cd backend && exec uv run fastapi dev app/main.py --port "$BACKEND_PORT") \
  > >(prefix backend 36) 2>&1 &
pids+=($!)

(cd frontend && exec pnpm dev --port "$FRONTEND_PORT" --strictPort) \
  > >(prefix frontend 35) 2>&1 &
pids+=($!)

if $open_browser; then
  open_dev_links_when_ready &
  opener_pid=$!
fi

# Si l'un des deux serveurs s'arrête (erreur, crash...), on arrête l'autre
wait -n "${pids[@]}" || true
echo "Un des serveurs s'est arrêté."
