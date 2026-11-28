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
    OFFICIAL_TEMPLATE_MAX_TAGS,
    TAG_MAX_LENGTH,
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


class SetForksAllowedRequest(BaseModel):
    """Whether other accounts may copy the template while it is public."""

    forks_allowed: bool


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

    tags: Annotated[list[TagLabel], Field(max_length=OFFICIAL_TEMPLATE_MAX_TAGS)]


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
    or deleted the image: `image_url` is then null. `image_status` is only shown to the owner, and
    `image_moderation_reason` only when the image is theirs, not one a copy took from another
    account."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool
    image_status: ImageStatus | None
    image_moderation_reason: str | None
    position: int


class TemplateResponse(BaseModel):
    """A template with its tiers and its tiles sorted by position, and its tags in their order.
    `max_tiles` and `max_tags` are the maximum numbers of tiles and tags; `first_made_public_at` is
    kept when the template goes back to private. `official` is true for a template owned by the
    site, edited by the super admins: `featured` is then true when it is in the TierList picks, and
    `editing_by_name` and `editing_until` name the super admin holding its edit lease, until when
    (both null when nobody holds it). `forks_allowed` is true when other accounts may copy it
    while it is public. `copied_from` is the name, when copied, of the template it was copied
    from, null when it is not a copy."""

    id: uuid.UUID
    name: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    tiers: list[TierResponse]
    tiles: list[TileResponse]
    max_tiles: int
    max_tags: int
    moderation: TemplateModeration
    moderation_reason: str | None
    visibility: TemplateVisibility
    first_made_public_at: datetime | None
    official: bool
    featured: bool
    editing_by_name: str | None
    editing_until: datetime | None
    forks_allowed: bool
    copied_from: str | None


class OfficialTemplateSummaryResponse(BaseModel):
    """An official template in the list of the moderation area: draft (`private`) or published
    (`public`), in the TierList picks or not, and the super admin editing it, if any."""

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime
    visibility: TemplateVisibility
    featured: bool
    editing_by_name: str | None


class OfficialTemplateLeaseResponse(BaseModel):
    """The edit lease of an official template, held by the caller until `editing_until`."""

    editing_by_name: str
    editing_until: datetime


class OfficialTemplateListResponse(BaseModel):
    """The official templates, most recently changed first."""

    items: list[OfficialTemplateSummaryResponse]


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
    """A page of the account's templates, most recently modified first. `next_cursor` reads the
    next page; it is null on the last one."""

    items: list[TemplateSummaryResponse]
    next_cursor: str | None


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
