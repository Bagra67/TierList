import uuid

from pydantic import BaseModel

from app.schemas.templates import TierResponse


class PublicTileResponse(BaseModel):
    """A tile of a public template, in the template's order. `image_removed` is true when moderation
    hid or deleted the image: `image_url` is then null."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool


class PublicTemplateResponse(BaseModel):
    """A public template as everyone sees it: its name, its owner's display name, its tags, its
    number of likes, its tiers and its tiles in their order."""

    id: uuid.UUID
    name: str
    owner_name: str
    tags: list[str]
    like_count: int
    tiers: list[TierResponse]
    tiles: list[PublicTileResponse]


class LikeStateResponse(BaseModel):
    """Whether the account likes the public template, and its number of likes."""

    liked: bool
    like_count: int


class MarketplaceTemplateResponse(BaseModel):
    """A card of the marketplace. The preview is the image of the first tile:
    `preview_image_removed` is true when moderation removed it, and both are empty when the first
    tile has no image. `tier_colors` are the colors of the tiers, top to bottom."""

    id: uuid.UUID
    name: str
    owner_name: str
    tags: list[str]
    tile_count: int
    like_count: int
    preview_image_url: str | None
    preview_image_removed: bool
    tier_colors: list[str]


class MarketplaceTemplateListResponse(BaseModel):
    """A page of the marketplace. `next_cursor` reads the next page with the same search, tag and
    sort; it is null on the last one."""

    items: list[MarketplaceTemplateResponse]
    next_cursor: str | None


class MarketplaceTagsResponse(BaseModel):
    """The tags used by the most public templates, most used first."""

    tags: list[str]
