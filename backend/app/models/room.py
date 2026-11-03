import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.rooms import ROOM_CODE_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import AutoAdvance, GameStatus, ItemOrder, RoomStatus

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.participant import Participant
    from app.models.room_ban import RoomBan
    from app.models.template import Template


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rooms"

    code: Mapped[str] = mapped_column(String(ROOM_CODE_LENGTH), unique=True)
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[RoomStatus] = mapped_column(
        text_enum(RoomStatus, "room_status"), default=RoomStatus.OPEN
    )

    item_order: Mapped[ItemOrder] = mapped_column(
        text_enum(ItemOrder, "item_order"), default=ItemOrder.TEMPLATE
    )
    auto_advance: Mapped[AutoAdvance] = mapped_column(
        text_enum(AutoAdvance, "auto_advance"), default=AutoAdvance.NONE
    )
    timer_seconds: Mapped[int]
    cooldown_seconds: Mapped[int]
    admin_plays: Mapped[bool] = mapped_column(default=True)
    late_arrivals_allowed: Mapped[bool] = mapped_column(default=True)
    version: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    template: Mapped[Template | None] = relationship()
    participants: Mapped[list[Participant]] = relationship(
        back_populates="room", cascade="all, delete-orphan", order_by="Participant.created_at"
    )
    bans: Mapped[list[RoomBan]] = relationship(
        cascade="all, delete-orphan", order_by="RoomBan.created_at"
    )
    current_game: Mapped[Game | None] = relationship(
        primaryjoin=f"and_(Game.room_id == Room.id, Game.status != '{GameStatus.CLOSED}')",
        viewonly=True,
        uselist=False,
    )
    closed_games: Mapped[list[Game]] = relationship(
        primaryjoin=f"and_(Game.room_id == Room.id, Game.status == '{GameStatus.CLOSED}')",
        viewonly=True,
        order_by="Game.closed_at.desc()",
    )
