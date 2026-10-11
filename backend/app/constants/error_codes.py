"""Codes d'erreur stables de l'API (champ code d'ErrorResponse).

Le frontend traduit l'erreur à partir de ce code et de ses params : ajouter un code demande
d'ajouter sa traduction dans chaque langue du frontend.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    # --- Erreurs génériques (app/core/errors.py) -------------------------------------------
    INTERNAL_ERROR = "internal_error"
    VALIDATION_ERROR = "validation_error"
    # HTTPException ordinaire, sans code dédié (ex. 404 ou 405 renvoyée par FastAPI)
    HTTP_ERROR = "http_error"

    # --- Santé -----------------------------------------------------------------------------
    DATABASE_UNAVAILABLE = "database_unavailable"

    # --- Authentification ------------------------------------------------------------------
    NOT_AUTHENTICATED = "not_authenticated"
    EMAIL_ALREADY_REGISTERED = "email_already_registered"
    INVALID_CREDENTIALS = "invalid_credentials"
    SESSION_EXPIRED = "session_expired"
    INCORRECT_PASSWORD = "incorrect_password"
    REAUTHENTICATION_REQUIRED = "reauthentication_required"
    # Lien envoyé par email invalide, expiré ou déjà utilisé
    INVALID_TOKEN = "invalid_token"
    # Code d'erreur de champ (FieldError) de la 422, avec le param min_length
    PASSWORD_TOO_SHORT = "password_too_short"

    # --- Templates -------------------------------------------------------------------------
    # Inexistant, supprimé ou à un autre utilisateur (indiscernables)
    TEMPLATE_NOT_FOUND = "template_not_found"
    # Tier inexistant dans ce template
    TIER_NOT_FOUND = "tier_not_found"
    # Suppression du dernier tier refusée : une tier list a au moins un tier
    LAST_TIER = "last_tier"
    # Tuile inexistante dans ce template
    TILE_NOT_FOUND = "tile_not_found"
    # Nombre maximal de tuiles atteint, avec le param max_tiles
    TILE_LIMIT_REACHED = "tile_limit_reached"

    # --- Images ----------------------------------------------------------------------------
    # Pas une image JPEG, PNG ou WebP, ou fichier illisible
    IMAGE_UNSUPPORTED_FORMAT = "image_unsupported_format"
    # Fichier trop lourd, avec le param max_bytes
    IMAGE_TOO_LARGE = "image_too_large"
    # Image décodée trop grande (bombe de décompression)
    IMAGE_TOO_MANY_PIXELS = "image_too_many_pixels"
