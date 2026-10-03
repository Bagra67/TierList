"""Format d'erreur unique de l'API : toute réponse d'erreur a la forme ErrorResponse."""

import logging
from collections.abc import Awaitable, Callable, Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.utils import is_body_allowed_for_status_code
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.exceptions.http import AppHTTPException, ErrorParamValue

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    message: str
    # Type d'erreur Pydantic (missing, string_too_short…) ou code dédié (password_too_short)
    code: str
    params: dict[str, ErrorParamValue] | None = None


class ErrorResponse(BaseModel):
    # Texte anglais pour les développeurs : le frontend traduit à partir de code et params
    detail: str
    code: str
    params: dict[str, ErrorParamValue] | None = None
    errors: list[FieldError] | None = None


def _scalar_params(context: Mapping[str, object] | None) -> dict[str, ErrorParamValue] | None:
    # Le contexte Pydantic peut contenir des objets (ex. l'exception d'un validateur) :
    # seules les valeurs simples, utiles à la traduction, sont exposées.
    if not context:
        return None
    params = {key: value for key, value in context.items() if isinstance(value, str | int | float)}
    return params or None


def _error_response(
    status_code: int, body: ErrorResponse, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=body.model_dump(exclude_none=True), headers=headers
    )


async def handle_http_exception(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, StarletteHTTPException)
    # Les en-têtes sont conservés : WWW-Authenticate, effacement du cookie de session…
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=exc.headers)
    if isinstance(exc, AppHTTPException):
        body = ErrorResponse(detail=str(exc.detail), code=exc.code, params=exc.params)
    else:
        body = ErrorResponse(detail=str(exc.detail), code=ErrorCode.HTTP_ERROR)
    return _error_response(exc.status_code, body, headers=exc.headers)


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        FieldError(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            code=error["type"],
            params=_scalar_params(error.get("ctx")),
        )
        for error in exc.errors()
    ]
    body = ErrorResponse(
        detail=messages.VALIDATION_ERROR, code=ErrorCode.VALIDATION_ERROR, errors=errors
    )
    return _error_response(422, body)


async def handle_unexpected_error(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Middleware plutôt qu'exception_handler(Exception) : Starlette relancerait l'exception
    # après la réponse, et uvicorn journaliserait la même trace une seconde fois.
    try:
        return await call_next(request)
    except Exception:  # dernier filet : toute exception non prévue devient une 500 générique
        logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        body = ErrorResponse(detail=messages.INTERNAL_ERROR, code=ErrorCode.INTERNAL_ERROR)
        return _error_response(500, body)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.middleware("http")(handle_unexpected_error)
