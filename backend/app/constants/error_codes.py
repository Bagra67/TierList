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
    # Template sans tuile : pas de partie possible avec
    TEMPLATE_HAS_NO_TILES = "template_has_no_tiles"
    # Tier inexistant dans ce template
    TIER_NOT_FOUND = "tier_not_found"
    # Suppression du dernier tier refusée : une tier list a au moins un tier
    LAST_TIER = "last_tier"
    # Tuile inexistante dans ce template
    TILE_NOT_FOUND = "tile_not_found"
    # Nombre maximal de tuiles atteint, avec le param max_tiles
    TILE_LIMIT_REACHED = "tile_limit_reached"
    # Tuile sans texte ni image
    TILE_EMPTY = "tile_empty"

    # --- Salles -----------------------------------------------------------------------------
    # Inexistante, fermée, ou dont l'utilisateur n'est pas participant (indiscernables)
    ROOM_NOT_FOUND = "room_not_found"
    # Action réservée au room admin
    ROOM_ADMIN_REQUIRED = "room_admin_required"
    # Réglage modifié pendant une partie (seules les arrivées peuvent l'être)
    ROOM_SETTINGS_LOCKED = "room_settings_locked"
    # Salle pleine, avec le param max_participants
    ROOM_FULL = "room_full"
    # Partie en cours et arrivées verrouillées par le room admin
    ROOM_LOCKED = "room_locked"
    # Pseudo d'invité déjà porté dans la salle (sans tenir compte de la casse)
    NICKNAME_TAKEN = "nickname_taken"
    # Lien perso d'invité inconnu, expiré ou d'une salle fermée
    GUEST_LINK_INVALID = "guest_link_invalid"
    # Participant inexistant dans cette salle (ou invité dont le lien a expiré)
    PARTICIPANT_NOT_FOUND = "participant_not_found"
    # Le room admin ne peut pas se retirer de sa salle
    CANNOT_REMOVE_ROOM_ADMIN = "cannot_remove_room_admin"
    # Compte ou navigateur d'invité banni de la salle ; aussi la raison de fermeture du canal
    ROOM_BANNED = "room_banned"
    # Bannissement inexistant dans cette salle
    BAN_NOT_FOUND = "ban_not_found"
    # Canal temps réel : message inattendu du client, pong absent, ou participant retiré par le
    # room admin (raisons de fermeture)
    INVALID_MESSAGE = "invalid_message"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    REMOVED_FROM_ROOM = "removed_from_room"

    # --- Parties ---------------------------------------------------------------------------
    # La salle a déjà une partie en cours
    GAME_IN_PROGRESS = "game_in_progress"
    # Aucun participant ne placerait les items (room admin seul, qui ne joue pas)
    NO_PLACING_PARTICIPANT = "no_placing_participant"
    # Aucun tour en cours : pas de partie, ou plus de tour à placer
    ROUND_NOT_IN_PROGRESS = "round_not_in_progress"
    # Le room admin qui ne joue pas ne place pas les items
    NOT_A_PLACING_PARTICIPANT = "not_a_placing_participant"
    # La tuile n'est pas l'item du tour en cours
    ITEM_NOT_CURRENT = "item_not_current"

    # --- Images ----------------------------------------------------------------------------
    # Pas une image JPEG, PNG ou WebP, ou fichier illisible
    IMAGE_UNSUPPORTED_FORMAT = "image_unsupported_format"
    # Fichier trop lourd, avec le param max_bytes
    IMAGE_TOO_LARGE = "image_too_large"
    # Image décodée trop grande (bombe de décompression)
    IMAGE_TOO_MANY_PIXELS = "image_too_many_pixels"
    # Trop d'envois sur l'heure écoulée, avec le param max_uploads
    IMAGE_UPLOAD_LIMIT_REACHED = "image_upload_limit_reached"
    # Image inexistante ou d'un autre utilisateur (indiscernables)
    IMAGE_NOT_FOUND = "image_not_found"
