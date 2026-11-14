import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.constants.templates import (
    TAG_MAX_LENGTH,
    TEMPLATE_MAX_TAGS,
    TEMPLATE_NAME_MAX_LENGTH,
    TIER_NAME_MAX_LENGTH,
    TILE_TEXT_MAX_LENGTH,
)
from app.models.enums import TemplateModeration, TemplateVisibility
from app.models.image import ImageStatus

TemplateName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TEMPLATE_NAME_MAX_LENGTH),
]


class CreateTemplateRequest(BaseModel):
    """Name of the new template; surrounding spaces are removed."""

    name: TemplateName


class RenameTemplateRequest(BaseModel):
    """New name of the template; surrounding spaces are removed."""

    name: TemplateName


class SetTemplateVisibilityRequest(BaseModel):
    """Visibility chosen for the template."""

    visibility: TemplateVisibility


TagLabel = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TAG_MAX_LENGTH),
]


class SetTemplateTagsRequest(BaseModel):
    """Every tag of the template, in the order to show them; they replace the current ones.
    Surrounding spaces are removed, and a tag equal to an earlier one ignoring case and accents is
    dropped."""

    tags: Annotated[list[TagLabel], Field(max_length=TEMPLATE_MAX_TAGS)]


TierName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TIER_NAME_MAX_LENGTH),
]

TierColor = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]

Position = Annotated[int, Field(ge=0)]


class UpdateTierRequest(BaseModel):
    """Changes to a tier: only the fields sent change. The color is in the #RRGGBB format."""

    name: TierName | None = None
    color: TierColor | None = None
    position: Position | None = None


TileText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TILE_TEXT_MAX_LENGTH),
]


class CreateTileRequest(BaseModel):
    """Content of the new tile: a text, an image or both, never neither."""

    text: TileText | None = None
    image_id: uuid.UUID | None = None


class UpdateTileRequest(BaseModel):
    """Changes to a tile: only the fields sent change. `null` removes the text or the image; the
    tile must keep one of the two."""

    text: TileText | None = None
    image_id: uuid.UUID | None = None
    position: Position | None = None


class TierResponse(BaseModel):
    """A tier of the template; position 0 is the top tier."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    position: int


class TileResponse(BaseModel):
    """A tile of the template, in the template's order. `image_removed` is true when moderation hid
    or deleted the image: `image_url` is then null. `image_status` and `image_moderation_reason` are
    only shown to the owner."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool
    image_status: ImageStatus | None
    image_moderation_reason: str | None
    position: int


class TemplateResponse(BaseModel):
    """A template with its tiers and its tiles sorted by position, and its tags in their order.
    `max_tiles` is the maximum number of tiles; `first_made_public_at` is kept when the template
    goes back to private."""

    id: uuid.UUID
    name: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    tiers: list[TierResponse]
    tiles: list[TileResponse]
    max_tiles: int
    moderation: TemplateModeration
    moderation_reason: str | None
    visibility: TemplateVisibility
    first_made_public_at: datetime | None


class RemovedImageResponse(BaseModel):
    """A tile whose image was hidden or deleted by moderation, with the decision and the reason."""

    model_config = ConfigDict(from_attributes=True)

    tile_id: uuid.UUID
    tile_text: str | None
    tile_position: int
    status: ImageStatus
    reason: str | None


class TemplateSummaryResponse(BaseModel):
    """A template in the account's list: its tags, its number of tiles, its moderation decision and
    the images removed from its tiles."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tags: list[str]
    tile_count: int
    updated_at: datetime
    moderation: TemplateModeration
    moderation_reason: str | None
    visibility: TemplateVisibility
    first_made_public_at: datetime | None
    removed_images: list[RemovedImageResponse]


class TemplateListResponse(BaseModel):
    """The account's templates, most recently modified first."""

    items: list[TemplateSummaryResponse]


class RemovedTemplateResponse(BaseModel):
    """A template deleted by moderation, not purged yet, with the date and the reason."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    removed_at: datetime
    reason: str


class RemovedTemplateListResponse(BaseModel):
    """The account's templates deleted by moderation and not purged yet."""

    items: list[RemovedTemplateResponse]
