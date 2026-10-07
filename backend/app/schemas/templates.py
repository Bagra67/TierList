import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.constants.templates import TEMPLATE_NAME_MAX_LENGTH

# Espaces de début et de fin retirés : un nom fait seulement d'espaces est un nom vide
TemplateName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TEMPLATE_NAME_MAX_LENGTH),
]


class CreateTemplateRequest(BaseModel):
    name: TemplateName


class RenameTemplateRequest(BaseModel):
    name: TemplateName


class TierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    # Format #RRGGBB
    color: str
    # 0 = en haut
    position: int


class TileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str | None
    # Ordre du template, 0 = première
    position: int


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    # Dernière modification du template, de ses tiers ou de ses tuiles
    updated_at: datetime
    # Triés par position
    tiers: list[TierResponse]
    tiles: list[TileResponse]


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


class TemplateListResponse(BaseModel):
    # Objet plutôt que tableau : une pagination pourra ajouter un champ sans casser le contrat
    items: list[TemplateSummaryResponse]
