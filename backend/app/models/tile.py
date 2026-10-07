import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TILE_TEXT_MAX_LENGTH
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.template import Template


class Tile(Base):
    """Un item à classer d'un template."""

    __tablename__ = "tiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), index=True
    )
    # None pour une tuile qui n'a qu'une image (l'image arrive avec les tuiles image)
    text: Mapped[str | None] = mapped_column(String(TILE_TEXT_MAX_LENGTH))
    # Ordre du template, 0 = première ; sans contrainte d'unicité, comme Tier.position
    position: Mapped[int]

    template: Mapped["Template"] = relationship(back_populates="tiles")
