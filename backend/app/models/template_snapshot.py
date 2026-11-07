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
    __tablename__ = "template_snapshots"

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    tiers: Mapped[list[SnapshotTier]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="SnapshotTier.position"
    )
    tiles: Mapped[list[SnapshotTile]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="SnapshotTile.position"
    )
