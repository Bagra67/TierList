import uuid
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.enums import GameStatus
from app.models.game import Game
from app.models.round import Round


def add_game(session: Session, game: Game) -> None:
    session.add(game)


def get_room_id_of_game(session: Session, game_id: uuid.UUID) -> uuid.UUID | None:
    """Salle de la partie ; None si la salle a été supprimée (la partie lui survit)."""
    return session.scalar(select(Game.room_id).where(Game.id == game_id))


def list_pending_round_deadlines(session: Session) -> list[tuple[uuid.UUID, int, datetime]]:
    """(partie, numéro du tour, fin du timer) des tours en cours qui attendent leur timer : à
    reprogrammer au démarrage du processus."""
    statement: Select[uuid.UUID, int, datetime | None] = (
        select(Game.id, Round.number, Round.ends_at)
        .join(Round, Round.game_id == Game.id)
        .where(
            Game.status == GameStatus.IN_ROUND,
            Round.number == Game.current_round_number,
            Round.ends_at.is_not(None),
            Round.ended_at.is_(None),
        )
    )
    deadlines: list[tuple[uuid.UUID, int, datetime]] = []
    for game_id, round_number, ends_at in session.execute(statement):
        # Toujours renseignée (filtre ci-dessus) ; le test la redit pour le typage
        if ends_at is not None:
            deadlines.append((game_id, round_number, ends_at))
    return deadlines
