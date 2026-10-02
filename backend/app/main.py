import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logging_settings
from app.db.session import get_db_session, ping_database

configure_logging(get_logging_settings().log_level)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TierList API",
    description="Backend FastAPI de l'application TierList",
    version="0.1.0",
)


class HelloResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


@app.get("/hello")
def hello() -> HelloResponse:
    return HelloResponse(message="Hello World")


@app.get("/health/db", responses={503: {"description": "Base de données indisponible"}})
def health_db(session: Annotated[Session, Depends(get_db_session)]) -> HealthResponse:
    try:
        ping_database(session)
    except SQLAlchemyError as exc:
        logger.exception("Échec de la connexion à la base de données")
        raise HTTPException(status_code=503, detail="Base de données indisponible") from exc
    return HealthResponse(status="ok")
