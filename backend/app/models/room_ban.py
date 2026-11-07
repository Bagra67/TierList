import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.rooms import GUEST_TOKEN_HASH_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RoomBan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "room_bans"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id"),
        CheckConstraint(
            "(user_id IS NULL) = (guest_token_hash IS NOT NULL)", name="account_or_guest"
        ),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    guest_token_hash: Mapped[str | None] = mapped_column(
        String(GUEST_TOKEN_HASH_LENGTH), unique=True
    )
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))

    @property
    def is_guest(self) -> bool:
        return self.user_id is None
