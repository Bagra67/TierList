from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUserDep, HistoryServiceDep
from app.api.presenters.games import past_games_response
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants.games import HISTORY_PAGE_SIZE_DEFAULT, HISTORY_PAGE_SIZE_MAX
from app.schemas.history import HistoryResponse
from app.services.history import HistoryPage

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", responses={**UNAUTHORIZED_RESPONSE})
def get_history(
    user: CurrentUserDep,
    service: HistoryServiceDep,
    limit: Annotated[int, Query(ge=1, le=HISTORY_PAGE_SIZE_MAX)] = HISTORY_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryResponse:
    """Les parties closes du compte, la plus récente en premier : celles où il a joué et celles des
    salles dont il était l'admin. Paginé par `limit` et `offset` ; `has_more` dit s'il reste des
    parties."""
    page: HistoryPage = service.history(user, limit, offset)
    return HistoryResponse(games=past_games_response(page.games), has_more=page.has_more)
