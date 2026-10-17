"""Items et tiers d'une partie, partagés par les réponses des salles et des résultats."""

from app.api.presenters.images import optional_image_url
from app.models.snapshot_tier import SnapshotTier
from app.models.snapshot_tile import SnapshotTile
from app.schemas.rooms import CurrentItemResponse, GameTierResponse
from app.services.image_storage import ImageStorage


def item_response(tile: SnapshotTile, storage: ImageStorage) -> CurrentItemResponse:
    """Un item de la partie : une tuile de la version figée, son texte et son image."""
    return CurrentItemResponse(
        id=tile.id, text=tile.text, image_url=optional_image_url(storage, tile.image)
    )


def tier_response(tier: SnapshotTier) -> GameTierResponse:
    return GameTierResponse(id=tier.id, name=tier.name, color=tier.color)
