from app.api.presenters.images import is_image_removed, optional_image_url
from app.models.snapshot_tier import SnapshotTier
from app.models.snapshot_tile import SnapshotTile
from app.schemas.rooms import CurrentItemResponse, GameTierResponse
from app.services.image_storage import ImageStorage


def item_response(tile: SnapshotTile, storage: ImageStorage) -> CurrentItemResponse:
    return CurrentItemResponse(
        id=tile.id,
        text=tile.text,
        image_url=optional_image_url(storage, tile.image),
        image_removed=is_image_removed(tile.image),
    )


def tier_response(tier: SnapshotTier) -> GameTierResponse:
    return GameTierResponse(id=tier.id, name=tier.name, color=tier.color)
