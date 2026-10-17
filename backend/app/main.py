import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, TypeAdapter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import SessionFactory, get_session_factory
from app.api.routes import auth, images, room_channel, rooms, templates
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse, register_error_handlers
from app.core.logging import configure_logging, get_logging_settings
from app.db.session import get_db_session, ping_database
from app.exceptions.http import AppHTTPException
from app.schemas.room_events import RoomClientMessage, RoomServerMessage
from app.services.games import GameService
from app.services.room_channel import room_connections
from app.services.rooms import RoomService
from app.services.round_timers import round_timers
from app.services.templates import TemplateService

configure_logging(get_logging_settings().log_level)

logger = logging.getLogger(__name__)


def _reset_presence(session_factory: SessionFactory) -> None:
    """Un processus qui démarre n'a aucun socket ouvert : personne n'est connecté."""
    try:
        with session_factory() as session:
            reset_count: int = RoomService(
                session, get_settings(), room_connections
            ).reset_presence()
    except SQLAlchemyError:
        # Base injoignable au démarrage : l'application démarre quand même (/health/db le dira)
        logger.warning("Présence non remise à zéro : base de données injoignable", exc_info=True)
        return
    logger.info("Présence remise à zéro au démarrage : %d participants", reset_count)


def _game_service(session: Session) -> GameService:
    """Service des parties hors requête (démarrage, timers) : mêmes dépendances que
    get_game_service, construites à la main faute d'injection."""
    settings: Settings = get_settings()
    rooms: RoomService = RoomService(session, settings, room_connections)
    return GameService(
        session, room_connections, rooms, TemplateService(session, settings), round_timers
    )


def _end_round_on_timer(
    session_factory: SessionFactory, game_id: uuid.UUID, round_number: int
) -> None:
    with session_factory() as session:
        _game_service(session).end_round_on_timer(game_id, round_number)


def _reschedule_rounds(session_factory: SessionFactory) -> None:
    """Un processus qui démarre n'a aucun timer : les échéances des tours en cours sont relues en
    base et reprogrammées (une échéance passée pendant l'arrêt se déclenche tout de suite)."""
    try:
        with session_factory() as session:
            deadlines: list[tuple[uuid.UUID, int, datetime]] = _game_service(
                session
            ).pending_round_deadlines()
    except SQLAlchemyError:
        logger.warning("Timers des tours non reprogrammés : base injoignable", exc_info=True)
        return
    for game_id, round_number, ends_at in deadlines:
        round_timers.schedule(game_id, round_number, ends_at)
    logger.info("Timers des tours reprogrammés au démarrage : %d", len(deadlines))


@asynccontextmanager
async def lifespan(started_app: FastAPI) -> AsyncIterator[None]:
    # Les dépendances ne sont pas injectées ici : la fabrique remplacée par les tests, s'il y en
    # a une, est reprise pour ne jamais toucher une autre base que la leur
    get_factory = started_app.dependency_overrides.get(get_session_factory, get_session_factory)
    session_factory: SessionFactory = get_factory()
    await run_in_threadpool(_reset_presence, session_factory)

    async def on_deadline(game_id: uuid.UUID, round_number: int) -> None:
        # La base est synchrone : la transition passe par le threadpool (realtime.md, §2.8)
        await run_in_threadpool(_end_round_on_timer, session_factory, game_id, round_number)

    round_timers.start(asyncio.get_running_loop(), on_deadline)
    await run_in_threadpool(_reschedule_rounds, session_factory)
    yield
    await round_timers.stop()


app = FastAPI(
    lifespan=lifespan,
    title="TierList API",
    description="Backend FastAPI de l'application TierList",
    version="0.5.0",
    # Toute route peut échouer de façon imprévue : la 500 générique figure dans le contrat
    responses={500: {"model": ErrorResponse, "description": messages.INTERNAL_ERROR}},
)
register_error_handlers(app)
app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(images.router)
app.include_router(rooms.router)
app.include_router(room_channel.router)


def _openapi_with_room_messages() -> dict[str, Any]:
    """Contrat de l'API, augmenté des messages du canal temps réel : ils ne passent par aucune
    route REST, mais le frontend en génère les types (pnpm gen:api)."""
    if app.openapi_schema:
        return app.openapi_schema
    schema: dict[str, Any] = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components: dict[str, Any] = schema.setdefault("components", {}).setdefault("schemas", {})
    for name, message_type in (
        ("RoomServerMessage", RoomServerMessage),
        ("RoomClientMessage", RoomClientMessage),
    ):
        message_schema: dict[str, Any] = TypeAdapter(message_type).json_schema(
            ref_template="#/components/schemas/{model}"
        )
        components.update(message_schema.pop("$defs", {}))
        components[name] = message_schema
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_room_messages  # type: ignore[method-assign]


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
