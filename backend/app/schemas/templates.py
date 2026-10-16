import uuid
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.constants.templates import (
    TEMPLATE_NAME_MAX_LENGTH,
    TIER_NAME_MAX_LENGTH,
    TILE_TEXT_MAX_LENGTH,
)

if TYPE_CHECKING:
    from app.models.image import Image

# Contexte de validation de TemplateResponse : la fonction qui donne l'adresse publique d'une
# image à partir de sa clé de stockage (ImageStorage.url)
IMAGE_URL_CONTEXT_KEY = "image_url"
ImageUrlBuilder = Callable[[str], str]

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


# Texte d'une tuile ; un texte fait seulement d'espaces est refusé (envoyer null pour n'en
# mettre aucun)
TileText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TILE_TEXT_MAX_LENGTH),
]


# Un texte, une image (envoyée avant par POST /images), ou les deux : sans aucun des deux, le
# service refuse la tuile (tile_empty)
class CreateTileRequest(BaseModel):
    text: TileText | None = None
    image_id: uuid.UUID | None = None


# Champs à changer : ceux qui sont absents restent tels quels. null retire le texte ou l'image
# (la tuile doit garder l'un des deux) ; une position null est ignorée
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
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str | None
    # Adresse publique de l'image compressée, None pour une tuile sans image. Lu depuis la
    # relation Tile.image ; l'URL est construite par la fonction IMAGE_URL_CONTEXT_KEY du
    # contexte de validation (l'adresse publique dépend des réglages, pas du modèle)
    image_url: str | None = Field(validation_alias="image")
    position: int

    @field_validator("image_url", mode="before")
    @classmethod
    def _image_public_url(cls, image: "Image | None", info: ValidationInfo) -> str | None:
        if image is None:
            return None
        if info.context is None or IMAGE_URL_CONTEXT_KEY not in info.context:
            raise RuntimeError("TileResponse needs the image URL builder in its context")
        image_url: ImageUrlBuilder = info.context[IMAGE_URL_CONTEXT_KEY]
        return image_url(image.storage_key)


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime
    tiers: list[TierResponse]
    tiles: list[TileResponse]
    # Nombre maximal de tuiles du template, affiché par l'éditeur
    max_tiles: int


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateSummaryResponse]
