import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.templates import TierResponse


class PublicTileResponse(BaseModel):
    """A tile of a public template, in the template's order. `image_removed` is true when moderation
    hid or deleted the image: `image_url` is then null."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool


class LineageAncestorResponse(BaseModel):
    """A template a copy comes from. `template_id` is set only while that template is listed,
    so it can be linked; `name` is its current name then, and the name it had when it was copied
    otherwise. `owner_name` is null once the template or its owner's account is gone."""

    model_config = ConfigDict(from_attributes=True)

    template_id: uuid.UUID | None
    name: str
    owner_name: str | None


class PublicTemplateResponse(BaseModel):
    """A public template as everyone sees it: its name, its owner's display name, its tags, its
    number of likes, its tiers and its tiles in their order. `featured` is true for an official
    template in the TierList picks. `copy_allowed` is true when its owner allows copies and it
    fits the limits of a copy. `lineage` lists the templates it was copied from, from its parent
    up to the original, empty for a template that is not a copy."""

    id: uuid.UUID
    name: str
    owner_name: str
    featured: bool
    tags: list[str]
    like_count: int
    tiers: list[TierResponse]
    tiles: list[PublicTileResponse]
    copy_allowed: bool
    lineage: list[LineageAncestorResponse]


class LikeStateResponse(BaseModel):
    """Whether the account likes the public template, its number of likes, and whether the account
    may like it (false for its owner)."""

    model_config = ConfigDict(from_attributes=True)

    liked: bool
    like_count: int
    can_like: bool


class TemplateLikeStateResponse(LikeStateResponse):
    """The like state of one public template, for the marketplace cards."""

    template_id: uuid.UUID


class LikeStatesResponse(BaseModel):
    """The like states of the requested templates that are listed, in the requested order; the
    others are left out."""

    items: list[TemplateLikeStateResponse]


class FavoriteStateResponse(BaseModel):
    """Whether the public template is in the account's favorites, and whether the account may add
    it (false for its owner)."""

    model_config = ConfigDict(from_attributes=True)

    favorited: bool
    can_favorite: bool


class TemplateFavoriteStateResponse(FavoriteStateResponse):
    """The favorite state of one public template, for the marketplace cards."""

    template_id: uuid.UUID


class FavoriteStatesResponse(BaseModel):
    """The favorite states of the requested templates that are listed, in the requested order; the
    others are left out."""

    items: list[TemplateFavoriteStateResponse]


class CopyStateResponse(BaseModel):
    """Whether the account may copy the public template: false for its owner, when copies are
    not allowed, or when it has more tiles or tags than a copy can keep."""

    can_copy: bool


class MarketplaceTemplateResponse(BaseModel):
    """A card of the marketplace. The preview is the image of the first tile:
    `preview_image_removed` is true when moderation removed it, and both are empty when the first
    tile has no image. `tier_colors` are the colors of the tiers, top to bottom. `featured` is true
    for an official template in the TierList picks. `copied_from` is the template it was copied
    from, null when it is not a copy."""

    id: uuid.UUID
    name: str
    owner_name: str
    featured: bool
    tags: list[str]
    tile_count: int
    like_count: int
    preview_image_url: str | None
    preview_image_removed: bool
    tier_colors: list[str]
    copied_from: LineageAncestorResponse | None


class MarketplaceTemplateListResponse(BaseModel):
    """A page of the marketplace. `next_cursor` reads the next page with the same search, tag and
    sort; it is null on the last one."""

    items: list[MarketplaceTemplateResponse]
    next_cursor: str | None


class FeaturedTemplatesResponse(BaseModel):
    """The TierList picks: the featured official templates that are listed, most recently featured
    first."""

    items: list[MarketplaceTemplateResponse]


class MarketplaceTagsResponse(BaseModel):
    """The tags used by the most public templates, most used first."""

    tags: list[str]
