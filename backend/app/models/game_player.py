import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.game import Game


class GamePlayer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "game_players"
    __table_args__ = (
        # Un compte joue au plus une fois une partie (les invités et les comptes supprimés,
        # sans user_id, n'y sont pas : NULL n'est jamais égal à NULL)
        UniqueConstraint("game_id", "user_id"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))

    game: Mapped[Game] = relationship(back_populates="players")
