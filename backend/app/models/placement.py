import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import PlacementPhase

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.game_player import GamePlayer
    from app.models.participant import Participant
    from app.models.snapshot_tile import SnapshotTile


class Placement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "placements"
    __table_args__ = (
        UniqueConstraint("game_id", "participant_id", "snapshot_tile_id", "phase"),
        UniqueConstraint("game_id", "player_id", "snapshot_tile_id", "phase"),
        CheckConstraint("(participant_id IS NULL) <> (player_id IS NULL)", name="seat_or_player"),
        CheckConstraint(
            "(snapshot_tier_id IS NULL) = (position IS NULL) AND position >= 0",
            name="tier_and_position",
        ),
        CheckConstraint(
            f"phase = '{PlacementPhase.ROUND}' OR snapshot_tier_id IS NOT NULL",
            name="final_not_absent",
        ),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )
    snapshot_tile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("snapshot_tiles.id"))
    phase: Mapped[PlacementPhase] = mapped_column(text_enum(PlacementPhase, "placement_phase"))
    snapshot_tier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("snapshot_tiers.id"))
    position: Mapped[int | None]

    game: Mapped[Game] = relationship(back_populates="placements")
    participant: Mapped[Participant | None] = relationship()
    player: Mapped[GamePlayer | None] = relationship()
    tile: Mapped[SnapshotTile] = relationship()

    @property
    def is_absent(self) -> bool:
        return self.snapshot_tier_id is None
