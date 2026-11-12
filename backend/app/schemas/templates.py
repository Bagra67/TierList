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
from app.models.enums import TemplateModeration, TemplateVisibility
from app.models.image import ImageStatus

TemplateName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TEMPLATE_NAME_MAX_LENGTH),
]


class CreateTemplateRequest(BaseModel):
    """Nom du nouveau modèle ; les espaces autour sont retirés."""

    name: TemplateName


class RenameTemplateRequest(BaseModel):
    """Nouveau nom du modèle ; les espaces autour sont retirés."""

    name: TemplateName


class SetTemplateVisibilityRequest(BaseModel):
    """Visibilité choisie pour le modèle."""

    visibility: TemplateVisibility


TierName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TIER_NAME_MAX_LENGTH),
]

TierColor = Annotated[
    str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"), AfterValidator(str.upper)
]

Position = Annotated[int, Field(ge=0)]


class UpdateTierRequest(BaseModel):
    """Changements d'un tier : seuls les champs envoyés changent. La couleur est au format
    #RRGGBB."""

    name: TierName | None = None
    color: TierColor | None = None
    position: Position | None = None


TileText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TILE_TEXT_MAX_LENGTH),
]


class CreateTileRequest(BaseModel):
    """Contenu de la nouvelle tuile : un texte, une image ou les deux, jamais aucun des deux."""

    text: TileText | None = None
    image_id: uuid.UUID | None = None


class UpdateTileRequest(BaseModel):
    """Changements d'une tuile : seuls les champs envoyés changent. `null` retire le texte ou
    l'image ; la tuile doit garder l'un des deux."""

    text: TileText | None = None
    image_id: uuid.UUID | None = None
    position: Position | None = None


class TierResponse(BaseModel):
    """Un tier du modèle ; la position 0 est le tier du haut."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    position: int


class TileResponse(BaseModel):
    """Une tuile du modèle, dans l'ordre du modèle. `image_removed` est vrai quand la modération a
    masqué ou supprimé l'image : `image_url` est alors null. `image_status` et
    `image_moderation_reason` ne sont montrés qu'au propriétaire."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool
    image_status: ImageStatus | None
    image_moderation_reason: str | None
    position: int


class TemplateResponse(BaseModel):
    """Un modèle avec ses tiers et ses tuiles triés par position. `max_tiles` est le nombre maximal
    de tuiles ; `first_made_public_at` est gardée quand le modèle repasse en privé."""

    id: uuid.UUID
    name: str
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
    """Une tuile dont l'image a été masquée ou supprimée par la modération, avec la décision et le
    motif."""

    model_config = ConfigDict(from_attributes=True)

    tile_id: uuid.UUID
    tile_text: str | None
    tile_position: int
    status: ImageStatus
    reason: str | None


class TemplateSummaryResponse(BaseModel):
    """Un modèle dans la liste du compte : son nombre de tuiles, sa décision de modération et les
    images retirées de ses tuiles."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime
    moderation: TemplateModeration
    moderation_reason: str | None
    visibility: TemplateVisibility
    first_made_public_at: datetime | None
    removed_images: list[RemovedImageResponse]


class TemplateListResponse(BaseModel):
    """Les modèles du compte, le plus récemment modifié en premier."""

    items: list[TemplateSummaryResponse]


class RemovedTemplateResponse(BaseModel):
    """Un modèle supprimé par la modération, pas encore purgé, avec la date et le motif."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    removed_at: datetime
    reason: str


class RemovedTemplateListResponse(BaseModel):
    """Les modèles du compte supprimés par la modération et pas encore purgés."""

    items: list[RemovedTemplateResponse]
