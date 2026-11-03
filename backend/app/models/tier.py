import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TIER_COLOR_LENGTH, TIER_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.template import Template


class Tier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tiers"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TIER_NAME_MAX_LENGTH))
    color: Mapped[str] = mapped_column(String(TIER_COLOR_LENGTH))
    position: Mapped[int]

    template: Mapped[Template] = relationship(back_populates="tiers")
