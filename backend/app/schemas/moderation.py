import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.models.enums import ModerationActionKind, ModerationTargetType, UserRole
from app.models.image import ImageStatus
from app.schemas.templates import TemplateSummaryResponse

# Motif écrit par le super admin : espaces de début et de fin retirés, 1 à 500 caractères
ModerationReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MODERATION_REASON_MAX_LENGTH),
]


class ModerationActionResponse(BaseModel):
    """Une entrée du journal de modération (US-1.9)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    # None une fois le compte du super admin supprimé ; actor_name reste
    actor_id: uuid.UUID | None
    actor_name: str
    action: ModerationActionKind
    target_type: ModerationTargetType
    # None si la cible n'a pas d'identifiant ; target_label reste lisible après sa suppression
    target_id: uuid.UUID | None
    target_label: str
    reason: str


class ModerationLogResponse(BaseModel):
    """Une page du journal de modération."""

    # De la plus récente à la plus ancienne
    entries: list[ModerationActionResponse]
    # Il reste des entrées après cette page : la suivante commence à offset + limit
    has_more: bool


class SuperAdminResponse(BaseModel):
    """Un super admin, pour filtrer le journal par auteur."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str


class ModerationReasonRequest(BaseModel):
    """Le motif d'une action de modération, écrit au journal (US-1.9)."""

    reason: ModerationReason


class RecentUploadResponse(BaseModel):
    """Une image des derniers envois (US-1.7)."""

    id: uuid.UUID
    # Adresse publique d'une image visible ; pour une image masquée, adresse signée et temporaire
    # de son fichier en quarantaine, que seuls les super admins reçoivent
    url: str
    # visible ou hidden : une image supprimée n'a plus de fichier et n'est jamais listée
    status: ImageStatus
    created_at: datetime
    # Mène à la page du compte de l'auteur ; None une fois son compte supprimé
    author_id: uuid.UUID | None
    # None une fois le compte de l'auteur supprimé
    author_name: str | None
    # Modèles non supprimés qui montrent l'image, par ordre alphabétique
    template_names: list[str]
    # Parties jouées avec l'image, en cours ou terminées
    game_count: int


class RecentUploadsResponse(BaseModel):
    """Une page des derniers envois."""

    # Des plus récentes aux plus anciennes
    images: list[RecentUploadResponse]
    # Il reste des images après cette page : la suivante commence à offset + limit
    has_more: bool


class AccountSummaryResponse(BaseModel):
    """Un compte dans la recherche des super admins (US-1.8)."""

    id: uuid.UUID
    display_name: str
    email: str
    created_at: datetime
    role: UserRole
    # Banni en ce moment
    banned: bool


class AccountSearchResponse(BaseModel):
    """Une page de la recherche de comptes, par nom."""

    accounts: list[AccountSummaryResponse]
    # Il reste des comptes après cette page : la suivante commence à offset + limit
    has_more: bool


class AccountBanResponse(BaseModel):
    """Le bannissement actif d'un compte."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    # Fin d'un bannissement temporaire ; None pour un bannissement définitif
    ends_at: datetime | None
    # Montré à la personne quand elle tente de se connecter
    reason: str
    actor_name: str


class AccountResponse(BaseModel):
    """La page d'un compte pour les super admins (US-1.8). Ses images se lisent par les derniers
    envois filtrés sur lui (owner_id), son historique par le journal filtré sur lui
    (account_id)."""

    id: uuid.UUID
    display_name: str
    email: str
    created_at: datetime
    email_verified: bool
    # Un super admin ne peut pas être sanctionné
    role: UserRole
    # Le bannissement actif, None si le compte n'est pas banni
    ban: AccountBanResponse | None
    # Ses templates actifs, avec leur état de modération
    templates: list[TemplateSummaryResponse]


class HiddenImagesResponse(BaseModel):
    """Résultat de « masquer toutes ses images »."""

    hidden_count: int


class BanAccountRequest(BaseModel):
    """Bannir un compte (US-1.8) : jusqu'à ends_at, ou définitivement sans date."""

    # Montré à la personne quand elle tente de se connecter
    reason: ModerationReason
    # Fin du bannissement, dans le futur et avec fuseau horaire ; absente pour un bannissement
    # définitif
    ends_at: AwareDatetime | None = None
