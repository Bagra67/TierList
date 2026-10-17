from fastapi import APIRouter

from app.api.dependencies import GameResultsServiceDep, ImageStorageDep
from app.api.presenters.results import game_results_response
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.games import GameResultsNotFoundError
from app.exceptions.http import AppHTTPException
from app.schemas.results import GameResultsResponse
from app.services.game_results import ClosedGameResults

router = APIRouter(prefix="/results", tags=["results"])


@router.get(
    "/{public_token}",
    responses={
        404: {"model": ErrorResponse, "description": messages.RESULTS_NOT_FOUND_DESCRIPTION}
    },
)
def get_game_results(
    public_token: str,
    service: GameResultsServiceDep,
    storage: ImageStorageDep,
    include_absent_votes: bool = True,
) -> GameResultsResponse:
    # Sans compte : le lien est la seule protection des résultats (US-5.3), donné aux places de la
    # salle par le lobby
    try:
        closed: ClosedGameResults = service.results(public_token, include_absent_votes)
    except GameResultsNotFoundError as exc:
        raise AppHTTPException(
            status_code=404, code=ErrorCode.RESULTS_NOT_FOUND, detail=messages.RESULTS_NOT_FOUND
        ) from exc
    return game_results_response(closed, storage)
