# Traitement des images des tuiles (docs/technical/images.md)

# Formats acceptés, reconnus d'après le contenu du fichier (noms des formats de Pillow). Refusés :
# GIF, SVG (peut contenir des scripts), HEIC et AVIF (décodeur supplémentaire nécessaire).
ACCEPTED_IMAGE_FORMATS: tuple[str, ...] = ("JPEG", "PNG", "WEBP")

# Plus grand côté de l'image stockée : une image plus grande est réduite, une plus petite agrandie
# (le plus grand affichage fait environ 150 px CSS, soit 450 pixels réels sur un écran 3x)
IMAGE_OUTPUT_MAX_SIDE_PX = 512
IMAGE_WEBP_QUALITY = 80

# --- Stockage ------------------------------------------------------------------------------
IMAGE_CONTENT_TYPE = "image/webp"
# Le contenu d'une clé ne change jamais (une nouvelle image a une nouvelle clé) : cache illimité
IMAGE_CACHE_CONTROL = "public, max-age=31536000, immutable"
IMAGE_FILE_EXTENSION = "webp"
# Longueur d'une clé de stockage : un UUID (36 caractères) suivi de « .webp »
IMAGE_STORAGE_KEY_MAX_LENGTH = 64
# Empreinte SHA-256 du fichier reçu, en hexadécimal
IMAGE_SHA256_LENGTH = 64
