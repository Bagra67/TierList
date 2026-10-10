import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.constants.templates import TEMPLATE_NAME_MAX_LENGTH, TIER_NAME_MAX_LENGTH

# Espaces de début et de fin retirés : un nom fait seulement d'espaces est un nom vide
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

# Couleur #RRGGBB, enregistrée en majuscules : #ff7f7f et #FF7F7F sont la même couleur
TierColor = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]

# 0 = en haut de la liste ; une position au-delà de la fin place le tier en dernier
Position = Annotated[int, Field(ge=0)]


# Champs à changer : ceux qui sont absents restent tels quels
class UpdateTierRequest(BaseModel):
    name: TierName | None = None
    color: TierColor | None = None
    position: Position | None = None


class TierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    position: int


class TileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str | None
    position: int


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    tiers: list[TierResponse]
    tiles: list[TileResponse]


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateSummaryResponse]
