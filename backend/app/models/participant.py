import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.rooms import GUEST_TOKEN_HASH_LENGTH, NICKNAME_INDEX
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.user import User


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id"),
        CheckConstraint(
            "(user_id IS NULL) = (nickname IS NOT NULL)"
            " AND (nickname IS NULL) = (guest_token_hash IS NULL)"
            " AND (nickname IS NULL) = (guest_expires_at IS NULL)",
            name="account_or_guest",
        ),
        Index(
            NICKNAME_INDEX,
            "room_id",
            func.lower(text("nickname")),
            unique=True,
            postgresql_where=text("nickname IS NOT NULL"),
        ),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    nickname: Mapped[str | None] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    guest_token_hash: Mapped[str | None] = mapped_column(
        String(GUEST_TOKEN_HASH_LENGTH), unique=True
    )
    guest_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    room: Mapped[Room] = relationship(back_populates="participants")
    user: Mapped[User | None] = relationship()

    @property
    def is_guest(self) -> bool:
        return self.user_id is None

    @property
    def display_name(self) -> str:
        if self.user is not None:
            return self.user.display_name
        if self.nickname is None:
            raise RuntimeError("A participant is either an account or a guest")
        return self.nickname

    def has_expired(self, now: datetime) -> bool:
        return self.guest_expires_at is not None and self.guest_expires_at <= now
