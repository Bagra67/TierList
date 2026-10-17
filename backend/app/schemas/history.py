from pydantic import BaseModel

from app.schemas.rooms import PastGameResponse


class HistoryResponse(BaseModel):
    """Une page de l'historique d'un compte (US-5.5)."""

    # De la plus récente à la plus ancienne
    games: list[PastGameResponse]
    # Il reste des parties après cette page : la suivante commence à offset + limit
    has_more: bool
