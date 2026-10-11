import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TILE_TEXT_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.image import Image
    from app.models.template import Template


class Tile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Un item à classer d'un template : un texte, une image, ou les deux (jamais aucun des
    deux, règle vérifiée par TemplateService)."""

    __tablename__ = "tiles"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), index=True
    )
    # None pour une tuile qui n'a qu'une image
    text: Mapped[str | None] = mapped_column(String(TILE_TEXT_MAX_LENGTH))
    # None pour une tuile qui n'a qu'un texte. Pas de ON DELETE : une image n'est effacée que
    # par le ramasse-miettes, une fois qu'aucune tuile ne l'utilise (docs/technical/images.md)
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("images.id"), index=True)
    # Ordre du template, 0 = première ; sans contrainte d'unicité, comme Tier.position
    position: Mapped[int]

    template: Mapped["Template"] = relationship(back_populates="tiles")
    # selectin : les images des tuiles d'un template se chargent en une requête (URL de la
    # réponse), pas une par tuile
    image: Mapped["Image | None"] = relationship(lazy="selectin")
