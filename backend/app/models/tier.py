import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TIER_COLOR_LENGTH, TIER_NAME_MAX_LENGTH
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.template import Template


class Tier(Base):
    """Une ligne de la tier list d'un template."""

    __tablename__ = "tiers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TIER_NAME_MAX_LENGTH))
    # Format #RRGGBB
    color: Mapped[str] = mapped_column(String(TIER_COLOR_LENGTH))
    # 0 = en haut. Sans contrainte d'unicité : un réordonnancement la violerait le temps de
    # décaler les autres tiers ; le service garde les positions continues.
    position: Mapped[int]

    template: Mapped["Template"] = relationship(back_populates="tiers")
