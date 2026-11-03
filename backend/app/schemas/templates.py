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
    TEMPLATE_NAME_MAX_LENGTH,
    TIER_NAME_MAX_LENGTH,
    TILE_TEXT_MAX_LENGTH,
)
from app.models.enums import TemplateModeration

TemplateName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TEMPLATE_NAME_MAX_LENGTH),
]


class CreateTemplateRequest(BaseModel):
    name: TemplateName


class RenameTemplateRequest(BaseModel):
    name: TemplateName


TierName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TIER_NAME_MAX_LENGTH),
]

TierColor = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]

Position = Annotated[int, Field(ge=0)]


class UpdateTierRequest(BaseModel):
    name: TierName | None = None
    color: TierColor | None = None
    position: Position | None = None


TileText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TILE_TEXT_MAX_LENGTH),
]


class CreateTileRequest(BaseModel):
    text: TileText | None = None
    image_id: uuid.UUID | None = None


class UpdateTileRequest(BaseModel):
    text: TileText | None = None
    image_id: uuid.UUID | None = None
    position: Position | None = None


class TierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    position: int


class TileResponse(BaseModel):
    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool
    position: int


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    tiers: list[TierResponse]
    tiles: list[TileResponse]
    max_tiles: int
    moderation: TemplateModeration
    moderation_reason: str | None


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime
    moderation: TemplateModeration
    moderation_reason: str | None


class TemplateListResponse(BaseModel):
    items: list[TemplateSummaryResponse]
