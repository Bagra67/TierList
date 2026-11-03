import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.images import IMAGE_SHA256_LENGTH, IMAGE_STORAGE_KEY_MAX_LENGTH
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum


class ImageStatus(StrEnum):
    """Statut de modération (#124) : toute image envoyée est visible."""

    VISIBLE = "visible"
    HIDDEN = "hidden"
    DELETED = "deleted"


class Image(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_owner_id_created_at", "owner_id", "created_at"),
        Index("ix_images_created_at", "created_at"),
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    storage_key: Mapped[str] = mapped_column(String(IMAGE_STORAGE_KEY_MAX_LENGTH), unique=True)
    width: Mapped[int]
    height: Mapped[int]
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(IMAGE_SHA256_LENGTH), index=True)
    status: Mapped[ImageStatus] = mapped_column(
        text_enum(ImageStatus, "image_status"), default=ImageStatus.VISIBLE
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
