import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tier import Tier
    from app.models.tile import Tile


class Template(Base):
    """Ce qu'on classe : ses tiers et ses tuiles. Privé à son propriétaire."""

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Supprimer le compte supprime ses templates, même ceux déjà supprimés logiquement
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # « Dernière modification » : onupdate ne couvre que la ligne du template ; le service la
    # met à jour lui-même quand un tier ou une tuile change.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Suppression logique : le template disparaît pour son propriétaire, puis est purgé
    # définitivement après DELETED_TEMPLATE_RETENTION_DAYS
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tiers: Mapped[list["Tier"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tier.position"
    )
    tiles: Mapped[list["Tile"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tile.position"
    )
