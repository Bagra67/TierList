"""Textes de l'API destinés aux développeurs (champ detail d'ErrorResponse, descriptions OpenAPI).

Ils sont en anglais et ne sont jamais affichés tels quels : le frontend traduit l'erreur à
partir de son code (app/constants/error_codes.py). Ils ne révèlent rien d'interne.
"""

# --- Erreurs génériques (app/core/errors.py) -----------------------------------------------
INTERNAL_ERROR = "Internal server error"
VALIDATION_ERROR = "Invalid request"

# --- Santé ---------------------------------------------------------------------------------
DATABASE_UNAVAILABLE = "Database unavailable"

# --- Authentification ----------------------------------------------------------------------
NOT_AUTHENTICATED = "Authentication required"
EMAIL_ALREADY_REGISTERED = "This email is already registered"
# Même message que l'email existe ou non : ne révèle pas quels comptes existent
INVALID_CREDENTIALS = "Incorrect email or password"
SESSION_EXPIRED = "Session expired, please sign in again"
INCORRECT_PASSWORD = "Incorrect password"
REAUTHENTICATION_REQUIRED = "Sign in again with Google to confirm the deletion"
INVALID_TOKEN = "Invalid or expired link"
# {min_length} est remplacé par la valeur de PASSWORD_MIN_LENGTH
PASSWORD_TOO_SHORT = "The password must be at least {min_length} characters long"

# --- Templates -----------------------------------------------------------------------------
TEMPLATE_NOT_FOUND = "Template not found"

# --- Descriptions des réponses dans le schéma OpenAPI --------------------------------------
UNAUTHORIZED_DESCRIPTION = "Not authenticated"
EMAIL_ALREADY_REGISTERED_DESCRIPTION = "Email already registered"
DELETE_ACCOUNT_FORBIDDEN_DESCRIPTION = "Incorrect password, or Google sign-in too old"
INVALID_TOKEN_DESCRIPTION = "Invalid or expired link"
TEMPLATE_NOT_FOUND_DESCRIPTION = "Template not found"
