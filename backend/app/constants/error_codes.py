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
