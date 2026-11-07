from app.api.presenters.images import (
    image_url_for_super_admin,
    is_image_removed,
    optional_image_url,
)
from app.models.image import ImageStatus
from app.models.template import Template
from app.models.tile import Tile
from app.schemas.moderation import ReviewedTemplateResponse, ReviewedTileResponse
from app.schemas.templates import TemplateResponse, TierResponse, TileResponse
from app.services.image_storage import ImageStorage
from app.services.template_moderation import ReviewedTemplate


def template_response(template: Template, storage: ImageStorage) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        created_at=template.created_at,
        updated_at=template.updated_at,
        tiers=[TierResponse.model_validate(tier) for tier in template.tiers],
        tiles=[_tile_response(tile, storage) for tile in template.tiles],
        max_tiles=template.max_tiles,
        moderation=template.moderation,
        moderation_reason=template.moderation_reason,
    )


def _tile_response(tile: Tile, storage: ImageStorage) -> TileResponse:
    return TileResponse(
        id=tile.id,
        text=tile.text,
        image_url=optional_image_url(storage, tile.image),
        image_removed=is_image_removed(tile.image),
        image_status=tile.image.status if tile.image is not None else None,
        image_moderation_reason=tile.image.moderation_reason if tile.image is not None else None,
        position=tile.position,
    )


def reviewed_template_response(
    reviewed: ReviewedTemplate, storage: ImageStorage
) -> ReviewedTemplateResponse:
    template: Template = reviewed.template
    return ReviewedTemplateResponse(
        id=template.id,
        name=template.name,
        updated_at=template.updated_at,
        owner_id=template.owner_id,
        owner_name=reviewed.owner_name,
        moderation=template.moderation,
        moderation_reason=template.moderation_reason,
        tiers=[TierResponse.model_validate(tier) for tier in template.tiers],
        tiles=[_reviewed_tile_response(tile, storage) for tile in template.tiles],
    )


def _reviewed_tile_response(tile: Tile, storage: ImageStorage) -> ReviewedTileResponse:
    has_file: bool = tile.image is not None and tile.image.status != ImageStatus.DELETED
    return ReviewedTileResponse(
        id=tile.id,
        text=tile.text,
        image_url=image_url_for_super_admin(storage, tile.image)
        if has_file and tile.image is not None
        else None,
        image_status=tile.image.status if tile.image is not None else None,
    )
