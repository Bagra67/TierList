from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH, EMAIL_MAX_LENGTH, PASSWORD_HASH_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(PASSWORD_HASH_MAX_LENGTH))
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_reset_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    role: Mapped[UserRole] = mapped_column(
        text_enum(UserRole, "user_role"), default=UserRole.USER, server_default=UserRole.USER
    )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN
