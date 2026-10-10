# --- Longueurs maximales (liées au schéma) -------------------------------------------------
TEMPLATE_NAME_MAX_LENGTH = 100
TIER_NAME_MAX_LENGTH = 50
# Couleur au format #RRGGBB
TIER_COLOR_LENGTH = 7
TILE_TEXT_MAX_LENGTH = 200

# --- Tiers d'un nouveau template, du haut vers le bas : (nom, couleur) ----------------------
DEFAULT_TIERS: tuple[tuple[str, str], ...] = (
    ("S", "#FF7F7F"),
    ("A", "#FFBF7F"),
    ("B", "#FFDF7F"),
    ("C", "#FFFF7F"),
    ("D", "#BFFF7F"),
    ("E", "#7FFF7F"),
)

# --- Tier ajouté par le propriétaire (en bas de la liste), à renommer et recolorer ensuite ------
NEW_TIER_NAME = "?"
NEW_TIER_COLOR = "#BFBFBF"
