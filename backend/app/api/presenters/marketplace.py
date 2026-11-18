from app.api.presenters.images import is_image_removed, optional_image_url
from app.models.template import Template
from app.models.tile import Tile
from app.schemas.marketplace import (
    MarketplaceTemplateResponse,
    PublicTemplateResponse,
    PublicTileResponse,
)
from app.schemas.templates import TierResponse
from app.services.image_storage import ImageStorage
from app.services.marketplace import MarketplaceTemplate, PublicTemplate


def public_template_response(
    public_template: PublicTemplate, storage: ImageStorage
) -> PublicTemplateResponse:
    template: Template = public_template.template
    return PublicTemplateResponse(
        id=template.id,
        name=template.name,
        owner_name=public_template.owner_name,
        tags=[tag.label for tag in template.tags],
        like_count=public_template.like_count,
        tiers=[TierResponse.model_validate(tier) for tier in template.tiers],
        tiles=[_public_tile_response(tile, storage) for tile in template.tiles],
    )


def _public_tile_response(tile: Tile, storage: ImageStorage) -> PublicTileResponse:
    return PublicTileResponse(
        id=tile.id,
        text=tile.text,
        image_url=optional_image_url(storage, tile.image),
        image_removed=is_image_removed(tile.image),
    )


def marketplace_template_response(
    item: MarketplaceTemplate, storage: ImageStorage
) -> MarketplaceTemplateResponse:
    template: Template = item.template
    first_tile: Tile | None = item.first_tile
    return MarketplaceTemplateResponse(
        id=template.id,
        name=template.name,
        owner_name=item.owner_name,
        tags=[tag.label for tag in template.tags],
        tile_count=item.tile_count,
        like_count=item.like_count,
        preview_image_url=None
        if first_tile is None
        else optional_image_url(storage, first_tile.image),
        preview_image_removed=first_tile is not None and is_image_removed(first_tile.image),
        tier_colors=[tier.color for tier in template.tiers],
    )
