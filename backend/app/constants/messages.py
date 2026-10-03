"""Textes renvoyés par l'API (champ detail d'ErrorResponse, descriptions OpenAPI).

Le frontend les affiche tels quels : ils sont en français, et ne révèlent rien d'interne.
"""

# --- Erreurs génériques (app/core/errors.py) -----------------------------------------------
INTERNAL_ERROR = "Erreur interne du serveur"
VALIDATION_ERROR = "Requête invalide"

# --- Santé ---------------------------------------------------------------------------------
DATABASE_UNAVAILABLE = "Base de données indisponible"

# --- Authentification ----------------------------------------------------------------------
NOT_AUTHENTICATED = "Authentification requise"
EMAIL_ALREADY_REGISTERED = "Cet email est déjà utilisé"
# Même message que l'email existe ou non : ne révèle pas quels comptes existent
INVALID_CREDENTIALS = "Email ou mot de passe incorrect"
SESSION_EXPIRED = "Session expirée, veuillez vous reconnecter"
INCORRECT_PASSWORD = "Mot de passe incorrect"
REAUTHENTICATION_REQUIRED = "Reconnectez-vous avec Google pour confirmer la suppression"
# {min_length} est remplacé par la valeur de PASSWORD_MIN_LENGTH
PASSWORD_TOO_SHORT = "Le mot de passe doit contenir au moins {min_length} caractères"

# --- Descriptions des réponses dans le schéma OpenAPI --------------------------------------
UNAUTHORIZED_DESCRIPTION = "Non authentifié"
EMAIL_ALREADY_REGISTERED_DESCRIPTION = "Email déjà utilisé"
DELETE_ACCOUNT_FORBIDDEN_DESCRIPTION = "Mot de passe incorrect, ou connexion Google trop ancienne"
