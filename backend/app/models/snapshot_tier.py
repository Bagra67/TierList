import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TIER_COLOR_LENGTH, TIER_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.template_snapshot import TemplateSnapshot


class SnapshotTier(UUIDPrimaryKeyMixin, Base):
    """Copie d'un tier dans une snapshot ; mêmes colonnes que Tier."""

    __tablename__ = "snapshot_tiers"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_snapshots.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TIER_NAME_MAX_LENGTH))
    # Format #RRGGBB
    color: Mapped[str] = mapped_column(String(TIER_COLOR_LENGTH))
    # 0 = en haut, positions continues recopiées du template
    position: Mapped[int]

    snapshot: Mapped["TemplateSnapshot"] = relationship(back_populates="tiers")
