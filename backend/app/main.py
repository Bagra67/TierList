import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes import auth, templates
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse, register_error_handlers
from app.core.logging import configure_logging, get_logging_settings
from app.db.session import get_db_session, ping_database
from app.exceptions.http import AppHTTPException

configure_logging(get_logging_settings().log_level)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TierList API",
    description="Backend FastAPI de l'application TierList",
    version="0.4.0",
    # Toute route peut échouer de façon imprévue : la 500 générique figure dans le contrat
    responses={500: {"model": ErrorResponse, "description": messages.INTERNAL_ERROR}},
)
register_error_handlers(app)
app.include_router(auth.router)
app.include_router(templates.router)


class HealthResponse(BaseModel):
    status: str


# Sonde de vie : ne dépend de rien, pour qu'une panne de la base ne fasse pas
# redémarrer en boucle une application qui fonctionne (Docker, hébergeur).
@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/health/db",
    responses={503: {"model": ErrorResponse, "description": messages.DATABASE_UNAVAILABLE}},
)
def health_db(session: Annotated[Session, Depends(get_db_session)]) -> HealthResponse:
    try:
        ping_database(session)
    except SQLAlchemyError as exc:
        logger.exception("Échec de la connexion à la base de données")
        raise AppHTTPException(
            status_code=503,
            code=ErrorCode.DATABASE_UNAVAILABLE,
            detail=messages.DATABASE_UNAVAILABLE,
        ) from exc
    return HealthResponse(status="ok")
