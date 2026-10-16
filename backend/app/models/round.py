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
    """Le moment où une tuile est montrée et placée par tous. Une partie a un tour par tuile de
    sa version figée, dans l'ordre des items fixé au démarrage (invariant 5)."""

    __tablename__ = "rounds"
    __table_args__ = (
        # La contrainte (game_id, number) sert aussi d'index sur game_id
        UniqueConstraint("game_id", "number"),
        UniqueConstraint("game_id", "snapshot_tile_id"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    # Rang dans l'ordre des items, à partir de 1
    number: Mapped[int]
    # Une tuile de la version figée, jamais celle du template
    snapshot_tile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("snapshot_tiles.id"), index=True)
    # None tant que le tour n'a pas commencé
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Fin du timer quand la salle en a un (auto_advance = timer) ; le serveur seul la décide
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Rempli quand le tour se termine (#93)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    game: Mapped["Game"] = relationship(back_populates="rounds")
    tile: Mapped["SnapshotTile"] = relationship()
