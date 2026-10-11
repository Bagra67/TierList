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
TIER_NOT_FOUND = "Tier not found"
LAST_TIER = "A template keeps at least one tier"
TILE_NOT_FOUND = "Tile not found"
# {max_tiles} est remplacé par la limite du plan
TILE_LIMIT_REACHED = "A template has at most {max_tiles} tiles"
TILE_EMPTY = "A tile needs a text or an image"

# --- Images --------------------------------------------------------------------------------
IMAGE_UNSUPPORTED_FORMAT = "The file is not a JPEG, PNG or WebP image"
# {max_bytes} est remplacé par IMAGE_UPLOAD_MAX_BYTES
IMAGE_TOO_LARGE = "The file is larger than {max_bytes} bytes"
IMAGE_TOO_MANY_PIXELS = "The image has too many pixels"
# {max_uploads} est remplacé par IMAGE_UPLOADS_PER_HOUR_MAX
IMAGE_UPLOAD_LIMIT_REACHED = "At most {max_uploads} images can be uploaded per hour"
IMAGE_NOT_FOUND = "Image not found"

# --- Descriptions des réponses dans le schéma OpenAPI --------------------------------------
UNAUTHORIZED_DESCRIPTION = "Not authenticated"
EMAIL_ALREADY_REGISTERED_DESCRIPTION = "Email already registered"
DELETE_ACCOUNT_FORBIDDEN_DESCRIPTION = "Incorrect password, or Google sign-in too old"
INVALID_TOKEN_DESCRIPTION = "Invalid or expired link"
TEMPLATE_NOT_FOUND_DESCRIPTION = "Template not found"
TEMPLATE_OR_TIER_NOT_FOUND_DESCRIPTION = "Template or tier not found"
LAST_TIER_DESCRIPTION = "The last tier of a template cannot be deleted"
TEMPLATE_OR_TILE_NOT_FOUND_DESCRIPTION = "Template or tile not found"
TILE_LIMIT_REACHED_DESCRIPTION = "Maximum number of tiles reached"
IMAGE_UNSUPPORTED_FORMAT_DESCRIPTION = "Not a JPEG, PNG or WebP image"
IMAGE_TOO_LARGE_DESCRIPTION = "File too large"
IMAGE_TOO_MANY_PIXELS_DESCRIPTION = "Image with too many pixels"
IMAGE_UPLOAD_LIMIT_REACHED_DESCRIPTION = "Too many images uploaded in the last hour"
TILE_EMPTY_DESCRIPTION = "Tile without text nor image, or invalid request"
TEMPLATE_OR_IMAGE_NOT_FOUND_DESCRIPTION = "Template or image not found"
TEMPLATE_TILE_OR_IMAGE_NOT_FOUND_DESCRIPTION = "Template, tile or image not found"
