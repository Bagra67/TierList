# --- Code de la salle (docs/technical/rooms.md) ---------------------------------------------
ROOM_CODE_LENGTH = 6
# Majuscules et chiffres, sans ceux qu'on confond en lisant ou en dictant un code (0/O, 1/I)
ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# Tirages avant d'abandonner : avec 32^6 (environ un milliard) de codes, une seule collision est
# déjà rare
ROOM_CODE_MAX_ATTEMPTS = 5

# Page de la salle côté frontend : le lien d'une salle est cette page suivie de son code (#84)
FRONTEND_ROOM = "/r"

# --- Invités (docs/technical/rooms.md, « Guests ») --------------------------------------------
# Octets aléatoires du jeton d'un invité (secrets.token_urlsafe), comme un refresh token
GUEST_TOKEN_BYTES = 32
# Longueur de son empreinte SHA-256 en hexadécimal, seule gardée en base
GUEST_TOKEN_HASH_LENGTH = 64
# Cookie HttpOnly qui fait reconnaître l'invité par son navigateur, un par salle
GUEST_COOKIE = "guest_token"
# Le lien perso porte le jeton dans le fragment (#guest=<jeton>), jamais envoyé au serveur
GUEST_LINK_FRAGMENT = "guest"
# Durée maximale du lien perso, en jours (docs/product/game-rules.md : 30 jours au plus)
GUEST_LINK_MAX_TTL_DAYS = 30

# --- Canal temps réel (docs/technical/realtime.md) ------------------------------------------
# Codes de fermeture du WebSocket (4000-4999), avec l'ErrorCode comme raison. Le client ne se
# reconnecte pas après NOT_AUTHENTICATED ni ROOM_NOT_FOUND.
CHANNEL_CLOSE_INVALID_MESSAGE = 4400
CHANNEL_CLOSE_NOT_AUTHENTICATED = 4401
CHANNEL_CLOSE_ROOM_NOT_FOUND = 4404
CHANNEL_CLOSE_HEARTBEAT_TIMEOUT = 4408

# --- Bornes des durées des réglages, en secondes -------------------------------------------
# Les valeurs par défaut sont dans Settings (ROOM_DEFAULT_*), qui doivent rester entre ces bornes
TIMER_SECONDS_MIN = 5
TIMER_SECONDS_MAX = 300
COOLDOWN_SECONDS_MIN = 10
COOLDOWN_SECONDS_MAX = 600
