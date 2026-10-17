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
    from app.models.snapshot_tile import SnapshotTile


class Placement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Où un participant a mis une tuile pendant une partie : un tier et une position dans ce
    tier, pour une phase. Un placement de tour peut être absent, sans tier ni position
    (docs/technical/games.md)."""

    __tablename__ = "placements"
    __table_args__ = (
        # Au plus un placement de tour et un placement final par tuile et participant (invariant 6)
        UniqueConstraint("game_id", "participant_id", "snapshot_tile_id", "phase"),
        # Un tier et une position, ou aucun des deux pour un vote absent (invariant 8)
        CheckConstraint(
            "(snapshot_tier_id IS NULL) = (position IS NULL) AND position >= 0",
            name="tier_and_position",
        ),
        # Seul un placement de tour peut être absent
        CheckConstraint(
            f"phase = '{PlacementPhase.ROUND}' OR snapshot_tier_id IS NOT NULL",
            name="final_not_absent",
        ),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    # CASCADE : retirer ou bannir un participant supprime ses placements, il n'est plus dans la
    # partie ni dans ses résultats
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    # Une tuile de la version figée, comme les tours
    snapshot_tile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("snapshot_tiles.id"))
    phase: Mapped[PlacementPhase] = mapped_column(text_enum(PlacementPhase, "placement_phase"))
    # None pour un vote absent
    snapshot_tier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("snapshot_tiers.id"))
    # Rang dans le tier pour ce participant et cette phase, 0 = premier. Sans contrainte
    # d'unicité : décaler les suivants la violerait le temps du décalage ; le service garde les
    # positions continues
    position: Mapped[int | None]

    game: Mapped["Game"] = relationship(back_populates="placements")
    tile: Mapped["SnapshotTile"] = relationship()

    @property
    def is_absent(self) -> bool:
        return self.snapshot_tier_id is None
