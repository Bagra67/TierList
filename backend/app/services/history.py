"""Historique d'un compte (US-5.5) : ses parties closes, page par page
(docs/technical/results.md)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.user import User
from app.repositories import games as game_repository


@dataclass(frozen=True)
class HistoryPage:
    # De la plus récente à la plus ancienne
    games: list[Game]
    # Il reste des parties après cette page
    has_more: bool


class HistoryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def history(self, user: User, limit: int, offset: int) -> HistoryPage:
        """Les parties closes du compte, à partir de offset : celles qu'il a jouées, et celles
        dont il était le room admin. Une partie de plus est lue pour savoir s'il en reste."""
        games: list[Game] = game_repository.list_history(self._session, user.id, limit + 1, offset)
        return HistoryPage(games=games[:limit], has_more=len(games) > limit)
