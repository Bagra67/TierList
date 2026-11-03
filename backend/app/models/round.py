import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.snapshot_tile import SnapshotTile


class Round(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint("game_id", "number"),
        UniqueConstraint("game_id", "snapshot_tile_id"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    number: Mapped[int]
    snapshot_tile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("snapshot_tiles.id"), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    game: Mapped[Game] = relationship(back_populates="rounds")
    tile: Mapped[SnapshotTile] = relationship()
