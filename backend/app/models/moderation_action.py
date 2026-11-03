import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.moderation import (
    MODERATION_REASON_MAX_LENGTH,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
)
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import ModerationActionKind, ModerationTargetType


class ModerationAction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "moderation_actions"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    action: Mapped[ModerationActionKind] = mapped_column(
        text_enum(ModerationActionKind, "moderation_action_kind")
    )
    target_type: Mapped[ModerationTargetType] = mapped_column(
        text_enum(ModerationTargetType, "moderation_target_type")
    )
    target_id: Mapped[uuid.UUID | None]
    target_label: Mapped[str] = mapped_column(String(MODERATION_TARGET_LABEL_MAX_LENGTH))
    reason: Mapped[str] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
