from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencies import GameResultsServiceDep, ImageStorageDep
from app.api.presenters.results import game_results_response
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.games import PUBLIC_RESULTS_TOKEN_MAX_LENGTH
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
    public_token: Annotated[str, Path(max_length=PUBLIC_RESULTS_TOKEN_MAX_LENGTH)],
    service: GameResultsServiceDep,
    storage: ImageStorageDep,
    include_absent_votes: bool = True,
) -> GameResultsResponse:
    """Les résultats d'une partie close, par son lien public : aucun compte n'est demandé, le token
    du lien est la seule protection. `include_absent_votes` choisit si les votes absents comptent
    dans le classement (oui par défaut) ; le calcul est refait à chaque requête."""
    try:
        closed: ClosedGameResults = service.results(public_token, include_absent_votes)
    except GameResultsNotFoundError as exc:
        raise AppHTTPException(
            status_code=404, code=ErrorCode.RESULTS_NOT_FOUND, detail=messages.RESULTS_NOT_FOUND
        ) from exc
    return game_results_response(closed, storage)
