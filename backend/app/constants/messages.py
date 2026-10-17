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

# --- Salles --------------------------------------------------------------------------------
TEMPLATE_HAS_NO_TILES = "The template has no tiles"
ROOM_NOT_FOUND = "Room not found"
ROOM_ADMIN_REQUIRED = "Only the room admin can do this"
ROOM_SETTINGS_LOCKED = "Only late arrivals can be changed during a game"
NICKNAME_TAKEN = "This nickname is already used in the room"
# {max_participants} est remplacé par la limite du plan
ROOM_FULL = "A room has at most {max_participants} participants"
ROOM_LOCKED = "A game is in progress and the room is locked"
GUEST_LINK_INVALID = "This guest link has expired or its room was closed"
PARTICIPANT_NOT_FOUND = "Participant not found in this room"
CANNOT_REMOVE_ROOM_ADMIN = "The room admin cannot be removed from their room"
ROOM_BANNED = "You are banned from this room"
BAN_NOT_FOUND = "Ban not found in this room"

# --- Parties -------------------------------------------------------------------------------
GAME_IN_PROGRESS = "A game is already in progress in this room"
NO_PLACING_PARTICIPANT = "A game needs at least one participant who places the items"
ROUND_NOT_IN_PROGRESS = "No round is in progress in this room"
NOT_A_PLACING_PARTICIPANT = "The room admin does not play: they do not place the items"
ITEM_NOT_CURRENT = "This tile is not the item of the current round"
ITEM_NOT_IN_GAME = "This tile is not an item of the game"
COOLDOWN_NOT_IN_PROGRESS = "The final cooldown is not in progress in this room"
COOLDOWN_OVER = "The final cooldown is over: nothing can be placed any more"
RESULTS_NOT_FOUND = "No closed game has this results link"

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
TEMPLATE_HAS_NO_TILES_DESCRIPTION = "Template without tiles"
ROOM_NOT_FOUND_DESCRIPTION = "Room not found"
ROOM_ADMIN_REQUIRED_DESCRIPTION = "Not the room admin"
ROOM_SETTINGS_LOCKED_DESCRIPTION = "Settings locked during a game, except late arrivals"
NICKNAME_TAKEN_DESCRIPTION = "Nickname already used in the room"
ROOM_FULL_OR_LOCKED_DESCRIPTION = "Room full, or locked during a game"
NOT_A_PLACING_PARTICIPANT_DESCRIPTION = "The room admin does not play"
ROOM_OR_TIER_NOT_FOUND_DESCRIPTION = "Room not found, or tier or tile not in the game"
ROUND_NOT_IN_PROGRESS_DESCRIPTION = "No round in progress (no game, or the cooldown has begun)"
CANNOT_PLACE_DESCRIPTION = (
    "No round nor cooldown in progress, the round or the cooldown is over,"
    " or during a round the tile is not the current item"
)
COOLDOWN_NOT_IN_PROGRESS_DESCRIPTION = "No final cooldown in progress"
RESULTS_NOT_FOUND_DESCRIPTION = "Unknown results link"
GAME_CANNOT_START_DESCRIPTION = (
    "Game already in progress, no participant who places, or template deleted or without tiles"
)
NICKNAME_TAKEN_OR_ROOM_FULL_OR_LOCKED_DESCRIPTION = (
    "Nickname already used, room full, or room locked during a game"
)
GUEST_LINK_INVALID_DESCRIPTION = "Guest link unknown, expired, or room closed"
ROOM_OR_PARTICIPANT_NOT_FOUND_DESCRIPTION = "Room or participant not found"
CANNOT_REMOVE_ROOM_ADMIN_DESCRIPTION = "The room admin cannot be removed"
ROOM_BANNED_DESCRIPTION = "Banned from the room"
ROOM_OR_BAN_NOT_FOUND_DESCRIPTION = "Room or ban not found"
