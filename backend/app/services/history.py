from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.user import User
from app.repositories import games as game_repository


@dataclass(frozen=True)
class HistoryPage:
    games: list[Game]
    has_more: bool


class HistoryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def history(self, user: User, limit: int, offset: int) -> HistoryPage:
        games: list[Game] = game_repository.list_history(self._session, user.id, limit + 1, offset)
        return HistoryPage(games=games[:limit], has_more=len(games) > limit)
