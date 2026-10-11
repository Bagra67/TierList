import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.snapshot_tier import SnapshotTier
    from app.models.snapshot_tile import SnapshotTile


class TemplateSnapshot(UUIDPrimaryKeyMixin, Base):
    """Copie figée des tiers et des tuiles d'un template, prise au démarrage d'une partie.

    Immuable : modifier, supprimer ou purger le template ne la change jamais, d'où l'absence de
    updated_at et de suppression logique (docs/technical/templates.md).
    """

    __tablename__ = "template_snapshots"

    # Template d'origine, pour information. SET NULL et non CASCADE : la purge du template
    # supprimé ou la suppression du compte ne doivent pas effacer les parties jouées avec
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), index=True
    )
    # Nom du template au moment de la copie
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    # clock_timestamp() comme TimestampMixin : l'heure réelle de la copie
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    tiers: Mapped[list["SnapshotTier"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="SnapshotTier.position"
    )
    tiles: Mapped[list["SnapshotTile"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="SnapshotTile.position"
    )
