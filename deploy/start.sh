#!/usr/bin/env bash
# Démarre TierList dans le pod (docs/technical/deployment.md). Copié à la racine du bundle de
# déploiement, lancé par le lanceur du pod (deploy/launcher.sh) ; peut aussi être lancé seul,
# depuis un bundle extrait : bash start.sh
#
# 1. installe uv dans $TIERLIST_HOME/bin s'il manque (sans root) ;
# 2. charge le fichier d'environnement ($TIERLIST_ENV_FILE) ;
# 3. installe les dépendances verrouillées (uv.lock), sans celles de développement ;
# 4. applique les migrations : en cas d'échec, le script s'arrête et l'application ne démarre pas ;
# 5. lance uvicorn, un seul worker (le registre temps réel est en mémoire).
#
# Idempotent : à chaque redémarrage, uv et les dépendances déjà installés sont réutilisés.
set -eu

# Version d'uv installée dans le pod ; celle du développement (uv --version)
UV_VERSION="0.12.22"

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
# Le port est aussi joignable sans passer par le tunnel : seules ces adresses peuvent annoncer le
# vrai client et le schéma (X-Forwarded-For, X-Forwarded-Proto). Jamais « * », qui laisserait
# n'importe qui se faire passer pour une autre adresse.
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
log "Démarrage d'uvicorn sur le port $SERVER_PORT (version ${APP_RELEASE:-inconnue})"
exec "$UV" run --no-sync uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$SERVER_PORT" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips "$TRUSTED_PROXY_IPS"
