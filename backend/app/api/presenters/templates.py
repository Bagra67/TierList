"""Réponses de l'API pour les templates, construites à partir des modèles."""

from app.api.presenters.images import is_image_removed, optional_image_url
from app.models.template import Template
from app.models.tile import Tile
from app.schemas.templates import TemplateResponse, TierResponse, TileResponse
from app.services.image_storage import ImageStorage


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
        position=tile.position,
    )
