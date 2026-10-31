#!/usr/bin/env bash
# Démarre TierList dans le pod (docs/technical/deployment.md). Copié à la racine du bundle de
# déploiement, lancé par le lanceur du pod (deploy/launcher.sh) ; peut aussi être lancé seul,
# depuis un bundle extrait : bash start.sh
#
# 1. installe uv dans $TIERLIST_HOME/bin s'il manque (sans root) ;
# 2. charge le fichier d'environnement ($TIERLIST_ENV_FILE) ;
# 3. installe les dépendances verrouillées (uv.lock), sans celles de développement ;
# 4. applique les migrations : en cas d'échec, le script s'arrête et l'application ne démarre pas ;
# 5. lance uvicorn, un seul worker (le registre temps réel est en mémoire). Les en-têtes de proxy
#    sont lus par l'application (app/core/proxy.py), qui refuse les connexions hors du tunnel.
#
# Idempotent : à chaque redémarrage, uv et les dépendances déjà installés sont réutilisés.
set -eu

# Version d'uv installée dans le pod ; celle du développement (uv --version)
UV_VERSION="0.13.6"

RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
# Dossier persistant du pod (/home/container) : uv, l'environnement Python et son cache y restent
# d'une version à l'autre. Sans lanceur, le dossier du bundle.
TIERLIST_HOME="${TIERLIST_HOME:-$RELEASE_DIR}"
TIERLIST_ENV_FILE="${TIERLIST_ENV_FILE:-$TIERLIST_HOME/.env}"
BIN_DIR="$TIERLIST_HOME/bin"
UV="$BIN_DIR/uv"

log() {
    printf '[start] %s\n' "$*"
}

install_uv() {
    log "Installation d'uv $UV_VERSION dans $BIN_DIR"
    mkdir -p "$BIN_DIR"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | env UV_UNMANAGED_INSTALL="$BIN_DIR" sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- "https://astral.sh/uv/$UV_VERSION/install.sh" | env UV_UNMANAGED_INSTALL="$BIN_DIR" sh
    else
        # Ni curl ni wget : le paquet uv de PyPI contient le même binaire
        rm -rf "$BIN_DIR/uv-pip"
        python3 -m pip install --quiet --disable-pip-version-check --target "$BIN_DIR/uv-pip" "uv==$UV_VERSION"
        cp "$BIN_DIR/uv-pip/bin/uv" "$UV"
        chmod +x "$UV"
    fi
}

if [ ! -x "$UV" ] || ! "$UV" --version | grep -q " $UV_VERSION"; then
    install_uv
fi

if [ -f "$TIERLIST_ENV_FILE" ]; then
    log "Variables d'environnement lues depuis $TIERLIST_ENV_FILE"
    set -a
    # shellcheck disable=SC1090 # chemin connu seulement à l'exécution
    . "$TIERLIST_ENV_FILE"
    set +a
else
    log "Pas de fichier $TIERLIST_ENV_FILE : seules les variables déjà définies sont utilisées"
fi

# Port donné par le panel de l'hébergeur ; 8000 hors du pod
if [ -z "${SERVER_PORT:-}" ]; then
    SERVER_PORT=8000
    log "SERVER_PORT non défini : port $SERVER_PORT"
fi
# Le port est aussi joignable sans passer par le tunnel : l'application ne sert que ces adresses
# (et la boucle locale), qui seules peuvent annoncer le vrai client et le schéma (X-Forwarded-For,
# X-Forwarded-Proto). Jamais « * », qui laisserait passer tout le monde.
if [ -z "${TRUSTED_PROXY_IPS:-}" ] || [ "$TRUSTED_PROXY_IPS" = "*" ]; then
    log "TRUSTED_PROXY_IPS doit lister les adresses du proxy (Cloudflare Tunnel), sans « * »"
    exit 1
fi

# Environnement Python partagé entre les versions (rapide après le premier démarrage), avec le
# Python du pod : uv ne télécharge pas d'autre interpréteur
export UV_PROJECT_ENVIRONMENT="$TIERLIST_HOME/.venv"
export UV_CACHE_DIR="$TIERLIST_HOME/.cache/uv"
export UV_PYTHON_DOWNLOADS=never

cd "$RELEASE_DIR/backend"
log "Installation des dépendances"
"$UV" sync --frozen --no-dev --python python3
log "Migrations de la base de données"
"$UV" run --no-sync alembic upgrade head
# Le panel MineStrator (egg Pterodactyl « python generic ») considère le pod démarré quand la
# console affiche exactement cette ligne
READY_LINE="change this part"
# Délai maximal d'attente de /api/health, en secondes : au-delà, la ligne n'est pas affichée,
# sans arrêter l'application (le panel montre alors le pod « en démarrage »)
READY_TIMEOUT_SECONDS=300

# Attend que l'application réponde, puis affiche READY_LINE une seule fois. Python plutôt que
# curl, absent de certaines images.
announce_ready() {
    if python3 - "$SERVER_PORT" "$READY_TIMEOUT_SECONDS" <<'PY'; then
import sys
import time
import urllib.request

port, timeout_seconds = sys.argv[1], float(sys.argv[2])
deadline = time.monotonic() + timeout_seconds
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
            if response.status == 200:
                sys.exit(0)
    except OSError:
        pass
    time.sleep(1)
sys.exit(1)
PY
        printf '%s\n' "$READY_LINE"
    else
        log "/api/health ne répond pas après ${READY_TIMEOUT_SECONDS} s : le panel n'est pas prévenu"
    fi
}

log "Démarrage d'uvicorn sur le port $SERVER_PORT (version ${APP_RELEASE:-inconnue})"
# En arrière-plan (double fork, détaché de ce shell) : uvicorn le remplace aussitôt avec exec et
# démarre pendant que la boucle attend ; son code de sortie n'arrête jamais le démarrage
(announce_ready &)
exec "$UV" run --no-sync uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$SERVER_PORT" \
    --workers 1 \
    --no-proxy-headers
