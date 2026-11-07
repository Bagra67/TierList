from pydantic import BaseModel

from app.schemas.rooms import PastGameResponse


class HistoryResponse(BaseModel):
    """Une page de l'historique d'un compte (US-5.5)."""

    games: list[PastGameResponse]
    has_more: bool
