import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import ItemOrder

if TYPE_CHECKING:
    from app.models.round import Round
    from app.models.template_snapshot import TemplateSnapshot


class GameStatus(StrEnum):
    """Cycle de vie d'une partie (docs/product/milestone-1/lifecycles.md)."""

    # Un item est montré, les participants le placent
    IN_ROUND = "in_round"
    # Après le dernier tour : chacun peut tout déplacer à nouveau (#96)
    COOLDOWN = "cooldown"
    # Finale : plus rien ne change (#98)
    CLOSED = "closed"


class Game(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une partie jouée sur une version figée d'un template, dans une salle : l'ordre des items
    et un tour par tuile (docs/technical/games.md)."""

    __tablename__ = "games"
    __table_args__ = (
        # Au plus une partie en cours par salle (invariant 3) ; le service le vérifie aussi
        Index(
            "uq_games_room_id_in_progress",
            "room_id",
            unique=True,
            postgresql_where=text("status <> 'closed'"),
        ),
    )

    # SET NULL et non CASCADE : une partie survit à sa salle (invariant 11). Sans index propre :
    # l'index partiel ci-dessus commence par room_id et sert aux recherches de la partie en cours
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    # La version figée du template, jamais modifiée ensuite (invariant 4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_snapshots.id"), index=True)
    status: Mapped[GameStatus] = mapped_column(
        text_enum(GameStatus, "game_status"), default=GameStatus.IN_ROUND
    )
    # Réglages de la salle au démarrage, gardés avec la partie : ils restent connus une fois la
    # salle fermée (le room admin qui ne joue pas est exclu des résultats)
    item_order: Mapped[ItemOrder] = mapped_column(text_enum(ItemOrder, "item_order"))
    admin_plays: Mapped[bool]
    # Numéro du tour en cours, à partir de 1
    current_round_number: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Rempli à la clôture (#98)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    snapshot: Mapped["TemplateSnapshot"] = relationship()
    rounds: Mapped[list["Round"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Round.number"
    )

    @property
    def current_round(self) -> "Round":
        return self.rounds[self.current_round_number - 1]
