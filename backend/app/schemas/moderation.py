import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.models.enums import ModerationActionKind, ModerationTargetType

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
