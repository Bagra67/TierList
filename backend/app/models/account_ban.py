import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountBan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "account_bans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    reason: Mapped[str] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
