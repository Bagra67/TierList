import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.models.enums import (
    ModerationActionKind,
    ModerationTargetType,
    ReportReason,
    TemplateModeration,
    UserRole,
)
from app.models.image import ImageStatus
from app.schemas.templates import TemplateSummaryResponse, TierResponse

ModerationReason = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MODERATION_REASON_MAX_LENGTH),
]


class ModerationActionResponse(BaseModel):
    """An entry of the moderation log (US-1.9)."""

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
    """A page of the moderation log."""

    entries: list[ModerationActionResponse]
    has_more: bool


class SuperAdminResponse(BaseModel):
    """A super admin, to filter the log by author."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str


class ModerationReasonRequest(BaseModel):
    """The reason for a moderation action, written to the log (US-1.9)."""

    reason: ModerationReason


class DismissReportsRequest(ModerationReasonRequest):
    """Dismiss the open reports of a content (US-1.3)."""

    target_type: ModerationTargetType
    target_id: uuid.UUID


class ReportReasonCountResponse(BaseModel):
    """A report reason and the number of reports that give it."""

    reason: ReportReason
    count: int


class ReportedContentResponse(BaseModel):
    """A reported content in the queue (US-1.3). It never tells who reported it."""

    target_type: ModerationTargetType
    target_id: uuid.UUID
    label: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    report_count: int
    reasons: list[ReportReasonCountResponse]
    details: list[str]
    first_reported_at: datetime
    image_url: str | None
    public_token: str | None


class ReportQueueResponse(BaseModel):
    """A page of the report queue, most reported first."""

    contents: list[ReportedContentResponse]
    has_more: bool


class OpenReportCountResponse(BaseModel):
    """The number of contents that have at least one open report."""

    open_contents: int


class RemoveNicknameRequest(ModerationReasonRequest):
    """Remove a reported nickname, permanently. target_id is the one of the report: an account, a
    participant or a player."""

    target_id: uuid.UUID


class HiddenGameResponse(BaseModel):
    """A game hidden by moderation: its results link cannot be found."""

    id: uuid.UUID
    template_name: str
    hidden_at: datetime


class HiddenGamesResponse(BaseModel):
    """A page of the hidden games, most recent first."""

    games: list[HiddenGameResponse]
    has_more: bool


class ReviewedTileResponse(BaseModel):
    """A tile read by a super admin: a hidden image stays visible in it, image_status says so."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_status: ImageStatus | None


class ReviewedTemplateResponse(BaseModel):
    """The content of a template for the super admins, even a private one (US-1.8)."""

    id: uuid.UUID
    name: str
    updated_at: datetime
    owner_id: uuid.UUID
    owner_name: str | None
    moderation: TemplateModeration
    moderation_reason: str | None
    tiers: list[TierResponse]
    tiles: list[ReviewedTileResponse]


class RecentUploadResponse(BaseModel):
    """An image of the latest uploads (US-1.7)."""

    id: uuid.UUID
    url: str
    status: ImageStatus
    created_at: datetime
    author_id: uuid.UUID | None
    author_name: str | None
    template_names: list[str]
    game_count: int


class RecentUploadsResponse(BaseModel):
    """A page of the latest uploads."""

    images: list[RecentUploadResponse]
    has_more: bool


class AccountSummaryResponse(BaseModel):
    """An account in the super admins' search (US-1.8)."""

    id: uuid.UUID
    display_name: str
    email: str
    created_at: datetime
    role: UserRole
    banned: bool


class AccountSearchResponse(BaseModel):
    """A page of the account search, by name."""

    accounts: list[AccountSummaryResponse]
    has_more: bool


class AccountBanResponse(BaseModel):
    """The active ban of an account."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    ends_at: datetime | None
    reason: str
    actor_name: str


class AccountPastBanResponse(AccountBanResponse):
    """A ban that was lifted, replaced by another one or that reached its end: lifted_at is empty in
    the last case."""

    lifted_at: datetime | None


class AccountResponse(BaseModel):
    """The page of an account for the super admins (US-1.8). Its images are read through the latest
    uploads filtered on it (owner_id), its history through the log filtered on it (account_id)."""

    id: uuid.UUID
    display_name: str
    email: str
    created_at: datetime
    email_verified: bool
    role: UserRole
    ban: AccountBanResponse | None
    past_bans: list[AccountPastBanResponse]
    templates: list[TemplateSummaryResponse]


class HiddenImagesResponse(BaseModel):
    """Result of a batch of "hide all their images": send the request again while `has_more` is
    true."""

    hidden_count: int
    has_more: bool


class BanAccountRequest(BaseModel):
    """Ban an account (US-1.8): until ends_at, or permanently without a date."""

    reason: ModerationReason
    ends_at: AwareDatetime | None = None
