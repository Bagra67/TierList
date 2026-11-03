TEMPLATE_NAME_MAX_LENGTH = 100
TIER_NAME_MAX_LENGTH = 50
TIER_COLOR_LENGTH = 7
TILE_TEXT_MAX_LENGTH = 200

# --- Tiers d'un nouveau template, du haut vers le bas : (nom, couleur) ----------------------
# Rampe de la charte : chaud en haut, froid en bas ; le texte encre (#1D1640) y garde 4,5:1.
# Les templates existants gardent leurs couleurs (ce sont des données).
DEFAULT_TIERS: tuple[tuple[str, str], ...] = (
    ("S", "#FF3B6B"),
    ("A", "#FF8A2A"),
    ("B", "#FFC22E"),
    ("C", "#7BD94A"),
    ("D", "#2EC4B6"),
    ("E", "#5B7CFA"),
)

NEW_TIER_NAME = "?"
NEW_TIER_COLOR = "#9AA0B4"

FREE_PLAN_MAX_TILES = 32
