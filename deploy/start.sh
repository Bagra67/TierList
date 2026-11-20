#!/usr/bin/env bash
# Démarre TierList dans le pod (docs/technical/deployment.md). Copié à la racine du bundle de
# déploiement, lancé par le superviseur du pod (deploy/supervisor.py) ; peut aussi être lancé seul,
# depuis un bundle extrait : bash start.sh
#
#   bash start.sh prepare   installe uv s'il manque (sans root), charge le fichier d'environnement
#                           ($TIERLIST_ENV_FILE), installe les dépendances verrouillées (uv.lock)
#                           dans l'environnement Python de cette version, applique les migrations ;
#                           pendant ce temps, la version précédente sert encore
#   bash start.sh serve     lance uvicorn, un seul worker (le registre temps réel est en mémoire),
#                           sur le socket ouvert par le superviseur ($TIERLIST_LISTEN_FD), sinon
#                           sur $SERVER_PORT. Les en-têtes de proxy sont lus par l'application
#                           (app/core/proxy.py), qui refuse les connexions hors du tunnel.
#   bash start.sh           les deux, pour essayer un bundle en local
#
# Idempotent : uv et le cache des paquets sont réutilisés d'une version à l'autre.
set -eu

# Version d'uv installée dans le pod ; celle du développement (uv --version)
UV_VERSION="0.13.6"

RELEASE_DIR="$(cd "$(dirname "$0")" && pwd)"
# Dossier persistant du pod (/home/container) : uv et son cache y restent
# d'une version à l'autre. Sans superviseur, le dossier du bundle.
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

# Un environnement Python par version : la préparation d'une version ne touche pas celui de la
# version qui sert encore. Le cache d'uv, partagé, rend l'installation rapide. Python du pod : uv
# ne télécharge pas d'autre interpréteur.
export UV_PROJECT_ENVIRONMENT="$RELEASE_DIR/.venv"
export UV_CACHE_DIR="$TIERLIST_HOME/.cache/uv"
export UV_PYTHON_DOWNLOADS=never

cd "$RELEASE_DIR/backend"

prepare() {
    log "Installation des dépendances"
    "$UV" sync --frozen --no-dev --python python3
    log "Migrations de la base de données"
    "$UV" run --no-sync alembic upgrade head
}

serve() {
    if [ -n "${TIERLIST_LISTEN_FD:-}" ]; then
        set -- --fd "$TIERLIST_LISTEN_FD"
        log "Démarrage d'uvicorn sur le socket du superviseur (version ${APP_RELEASE:-inconnue})"
    else
        set -- --host 0.0.0.0 --port "$SERVER_PORT"
        log "Démarrage d'uvicorn sur le port $SERVER_PORT (version ${APP_RELEASE:-inconnue})"
    fi
    # Le Python de l'environnement directement, sans uv run : le superviseur arrête ce processus,
    # qui doit être uvicorn lui-même pour recevoir le signal
    exec "$UV_PROJECT_ENVIRONMENT/bin/python" -m uvicorn app.main:app "$@" \
        --workers 1 \
        --no-proxy-headers \
        --timeout-graceful-shutdown "$GRACEFUL_SHUTDOWN_SECONDS"
}

GRACEFUL_SHUTDOWN_SECONDS=5

case "${1:-all}" in
    prepare) prepare ;;
    serve) serve ;;
    all)
        prepare
        serve
        ;;
    *)
        log "Usage : bash start.sh [prepare|serve]"
        exit 2
        ;;
esac
