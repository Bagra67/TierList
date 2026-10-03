"""Format d'erreur unique de l'API : toute réponse d'erreur a la forme ErrorResponse."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.constants import messages

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    detail: str
    errors: list[FieldError] | None = None


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        FieldError(field=".".join(str(part) for part in error["loc"]), message=error["msg"])
        for error in exc.errors()
    ]
    body = ErrorResponse(detail=messages.VALIDATION_ERROR, errors=errors)
    return JSONResponse(status_code=422, content=body.model_dump(exclude_none=True))


async def handle_unexpected_error(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Middleware plutôt qu'exception_handler(Exception) : Starlette relancerait l'exception
    # après la réponse, et uvicorn journaliserait la même trace une seconde fois.
    try:
        return await call_next(request)
    except Exception:  # dernier filet : toute exception non prévue devient une 500 générique
        logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        body = ErrorResponse(detail=messages.INTERNAL_ERROR)
        return JSONResponse(status_code=500, content=body.model_dump(exclude_none=True))


def register_error_handlers(app: FastAPI) -> None:
    """HTTPException garde le format {"detail": ...} de FastAPI, déjà conforme à ErrorResponse."""
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.middleware("http")(handle_unexpected_error)
