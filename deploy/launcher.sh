#!/usr/bin/env bash
# Lanceur du pod (docs/technical/deployment.md) : envoyé par le déploiement dans le dossier de
# travail du pod sous le nom start.sh, et lancé par sa commande de démarrage (bash start.sh).
#
# Le déploiement envoie par SFTP, qui ne sait ni extraire une archive ni lancer une commande :
#   releases/tierlist-<version>.tar.gz   le bundle de la version
#   supervisor.py                        le superviseur (deploy/supervisor.py)
#   .env                                 les réglages de l'environnement
#   CURRENT                              le nom de la version à lancer, écrit en dernier
# Le superviseur garde le port ouvert, sert la version de CURRENT et passe à la suivante quand
# CURRENT change, sans redémarrer le pod.
set -eu

TIERLIST_HOME="$(cd "$(dirname "$0")" && pwd)"
export TIERLIST_HOME
exec python3 -u "$TIERLIST_HOME/supervisor.py"
