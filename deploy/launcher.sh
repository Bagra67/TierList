#!/usr/bin/env bash
# Lanceur du pod (docs/technical/deployment.md) : envoyé par le déploiement dans le dossier de
# travail du pod sous le nom start.sh, et lancé par sa commande de démarrage (bash start.sh).
#
# Le déploiement envoie par SFTP, qui ne sait ni extraire une archive ni (pas toujours) créer un
# lien symbolique :
#   releases/tierlist-<version>.tar.gz   le bundle de la version
#   .env                                 les réglages de l'environnement
#   CURRENT                              le nom de la version à lancer, écrit en dernier
# Ce lanceur extrait la version de CURRENT si besoin, ne garde que les dernières versions, puis
# passe la main au start.sh du bundle. Un retour arrière réécrit CURRENT et redémarre le pod.
set -eu

# Versions gardées dans releases/ (archive et dossier extrait), celle de CURRENT comprise
KEEP_RELEASES=3

TIERLIST_HOME="$(cd "$(dirname "$0")" && pwd)"
RELEASES_DIR="$TIERLIST_HOME/releases"

log() {
    printf '[launcher] %s\n' "$*"
}

if [ ! -f "$TIERLIST_HOME/CURRENT" ]; then
    log "Fichier CURRENT absent : aucune version déployée"
    exit 1
fi
version="$(tr -d '[:space:]' <"$TIERLIST_HOME/CURRENT")"
# Le nom sert de chemin : rien qui puisse sortir de releases/
if ! printf '%s' "$version" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$'; then
    log "Version invalide dans CURRENT : « $version »"
    exit 1
fi

release_dir="$RELEASES_DIR/$version"
if [ ! -f "$release_dir/start.sh" ]; then
    archive="$RELEASES_DIR/tierlist-$version.tar.gz"
    if [ ! -f "$archive" ]; then
        log "Archive introuvable : $archive"
        exit 1
    fi
    log "Extraction de $archive"
    # Extraction à côté puis renommage : un arrêt en cours de route ne laisse pas de version à
    # moitié extraite, que le prochain démarrage prendrait pour complète
    staging_dir="$RELEASES_DIR/.extract-$version"
    rm -rf "$staging_dir" "$release_dir"
    mkdir -p "$staging_dir"
    tar -xzf "$archive" -C "$staging_dir"
    mv "$staging_dir/tierlist-$version" "$release_dir"
    rm -rf "$staging_dir"
fi

# Les plus récentes d'abord ; la version lancée n'est jamais supprimée
kept=1
for archive in $(ls -1t "$RELEASES_DIR"/tierlist-*.tar.gz 2>/dev/null); do
    old_version="${archive##*/tierlist-}"
    old_version="${old_version%.tar.gz}"
    [ "$old_version" = "$version" ] && continue
    if [ "$kept" -lt "$KEEP_RELEASES" ]; then
        kept=$((kept + 1))
        continue
    fi
    log "Suppression de l'ancienne version $old_version"
    rm -rf "$archive" "${RELEASES_DIR:?}/$old_version"
done

export TIERLIST_HOME
export TIERLIST_ENV_FILE="$TIERLIST_HOME/.env"
log "Lancement de la version $version"
exec bash "$release_dir/start.sh"
