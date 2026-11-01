"""Modération (docs/technical/moderation.md)."""

# --- Journal de modération (US-1.9) ---------------------------------------------------------
# Motif d'une action, écrit par le super admin
MODERATION_REASON_MAX_LENGTH = 500
# Libellé de la cible, copié au moment de l'action (nom d'un modèle, d'un compte, pseudo…) : il
# reste lisible quand la cible est supprimée
MODERATION_TARGET_LABEL_MAX_LENGTH = 200
# Entrées par page : la première page par défaut, et la plus grande qu'un client peut demander
MODERATION_LOG_PAGE_SIZE_DEFAULT = 50
MODERATION_LOG_PAGE_SIZE_MAX = 100
