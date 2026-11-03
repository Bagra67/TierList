import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.models.enums import ModerationActionKind, ModerationTargetType, UserRole
from app.models.image import ImageStatus
from app.schemas.templates import TemplateSummaryResponse

ModerationReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MODERATION_REASON_MAX_LENGTH),
]


class ModerationActionResponse(BaseModel):
    """Une entrée du journal de modération (US-1.9)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID | None
    actor_name: str
    action: ModerationActionKind
    target_type: ModerationTargetType
    target_id: uuid.UUID | None
    target_label: str
    reason: str


class ModerationLogResponse(BaseModel):
    """Une page du journal de modération."""

    entries: list[ModerationActionResponse]
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
    url: str
    status: ImageStatus
    created_at: datetime
    author_id: uuid.UUID | None
    author_name: str | None
    template_names: list[str]
    game_count: int


class RecentUploadsResponse(BaseModel):
    """Une page des derniers envois."""

    images: list[RecentUploadResponse]
    has_more: bool


class AccountSummaryResponse(BaseModel):
    """Un compte dans la recherche des super admins (US-1.8)."""

    id: uuid.UUID
    display_name: str
    email: str
    created_at: datetime
    role: UserRole
    banned: bool


class AccountSearchResponse(BaseModel):
    """Une page de la recherche de comptes, par nom."""

    accounts: list[AccountSummaryResponse]
    has_more: bool


class AccountBanResponse(BaseModel):
    """Le bannissement actif d'un compte."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    ends_at: datetime | None
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
    role: UserRole
    ban: AccountBanResponse | None
    templates: list[TemplateSummaryResponse]


class HiddenImagesResponse(BaseModel):
    """Résultat de « masquer toutes ses images »."""

    hidden_count: int


class BanAccountRequest(BaseModel):
    """Bannir un compte (US-1.8) : jusqu'à ends_at, ou définitivement sans date."""

    reason: ModerationReason
    ends_at: AwareDatetime | None = None
