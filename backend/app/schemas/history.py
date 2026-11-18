from pydantic import BaseModel

from app.schemas.rooms import PastGameResponse


class HistoryResponse(BaseModel):
    """A page of an account's history (US-5.5)."""

    games: list[PastGameResponse]
    has_more: bool
