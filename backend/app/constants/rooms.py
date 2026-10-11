# --- Code de la salle (docs/technical/rooms.md) ---------------------------------------------
ROOM_CODE_LENGTH = 6
# Majuscules et chiffres, sans ceux qu'on confond en lisant ou en dictant un code (0/O, 1/I)
ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# Tirages avant d'abandonner : avec 32^6 (environ un milliard) de codes, une seule collision est
# déjà rare
ROOM_CODE_MAX_ATTEMPTS = 5

# Page de la salle côté frontend : le lien d'une salle est cette page suivie de son code (#84)
FRONTEND_ROOM = "/r"

# --- Bornes des durées des réglages, en secondes -------------------------------------------
# Les valeurs par défaut sont dans Settings (ROOM_DEFAULT_*), qui doivent rester entre ces bornes
TIMER_SECONDS_MIN = 5
TIMER_SECONDS_MAX = 300
COOLDOWN_SECONDS_MIN = 10
COOLDOWN_SECONDS_MAX = 600
