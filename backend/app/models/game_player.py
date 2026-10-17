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
    """Un joueur d'une partie close, figé à la clôture (US-5.1) : ses placements lui sont
    rattachés au lieu de sa place, qui peut disparaître ensuite (salle fermée, place retirée,
    compte supprimé) sans rien changer à la partie (docs/technical/games.md)."""

    __tablename__ = "game_players"
    __table_args__ = (
        # Un compte joue au plus une fois une partie (les invités et les comptes supprimés,
        # sans user_id, n'y sont pas : NULL n'est jamais égal à NULL)
        UniqueConstraint("game_id", "user_id"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    # Le compte du joueur, pour son historique (#103) ; None pour un invité. SET NULL : supprimer
    # le compte garde la partie et son classement pour les autres
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Nom au moment de la clôture, pour les résultats (un invité n'en a pas d'autre)
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))

    game: Mapped["Game"] = relationship(back_populates="players")
