import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, query_expression, relationship

from app.constants.games import PUBLIC_RESULTS_TOKEN_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import GameStatus, ItemOrder

if TYPE_CHECKING:
    from app.models.game_player import GamePlayer
    from app.models.placement import Placement
    from app.models.round import Round
    from app.models.template_snapshot import TemplateSnapshot


class Game(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "games"
    __table_args__ = (
        Index(
            "uq_games_room_id_in_progress",
            "room_id",
            unique=True,
            postgresql_where=text(f"status <> '{GameStatus.CLOSED}'"),
        ),
        CheckConstraint(
            f"status <> '{GameStatus.CLOSED}' OR public_token IS NOT NULL",
            name="closed_has_public_token",
        ),
        Index(
            "ix_games_hidden_at",
            "hidden_at",
            postgresql_where=text("hidden_at IS NOT NULL"),
        ),
    )

    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template_snapshots.id"), index=True)
    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[GameStatus] = mapped_column(
        text_enum(GameStatus, "game_status"), default=GameStatus.IN_ROUND
    )
    item_order: Mapped[ItemOrder] = mapped_column(text_enum(ItemOrder, "item_order"))
    admin_plays: Mapped[bool]
    current_round_number: Mapped[int]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cooldown_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    public_token: Mapped[str | None] = mapped_column(
        String(PUBLIC_RESULTS_TOKEN_MAX_LENGTH), unique=True
    )
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    snapshot: Mapped[TemplateSnapshot] = relationship()
    rounds: Mapped[list[Round]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Round.number"
    )
    placements: Mapped[list[Placement]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Placement.created_at"
    )
    players: Mapped[list[GamePlayer]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="GamePlayer.created_at"
    )
    player_count: Mapped[int | None] = query_expression()

    @property
    def current_round(self) -> Round:
        return self.rounds[self.current_round_number - 1]
