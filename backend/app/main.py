import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, TypeAdapter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dependencies import (
    SessionFactory,
    SettingsDep,
    build_game_service,
    get_session_factory,
)
from app.api.routes import auth, history, images, results, room_channel, rooms, templates
from app.constants import messages
from app.constants.api import API_PREFIX
from app.constants.error_codes import ErrorCode
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse, handle_http_exception, register_error_handlers
from app.core.frontend import mount_frontend
from app.core.logging import configure_logging, get_logging_settings
from app.db.session import get_db_session, ping_database
from app.exceptions.http import AppHTTPException
from app.schemas.room_events import RoomClientMessage, RoomServerMessage
from app.services.games import GameService
from app.services.image_storage import create_image_storage
from app.services.maintenance import purge_deleted_templates, purge_unused_images
from app.services.nightly_scheduler import nightly_scheduler
from app.services.room_channel import room_connections
from app.services.room_sweeper import room_sweeper
from app.services.rooms import RoomService
from app.services.round_timers import round_timers

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
    """Service des parties pour le démarrage et les timers : les sockets et les timers de ce
    processus."""
    return build_game_service(session, get_settings(), room_connections, round_timers)


def _end_round_on_timer(
    session_factory: SessionFactory, game_id: uuid.UUID, round_number: int
) -> None:
    with session_factory() as session:
        _game_service(session).end_round_on_timer(game_id, round_number)


def _end_cooldown_on_timer(session_factory: SessionFactory, game_id: uuid.UUID) -> None:
    with session_factory() as session:
        _game_service(session).end_cooldown_on_timer(game_id)


def _close_inactive_rooms(session_factory: SessionFactory) -> None:
    inactive_for: timedelta = timedelta(hours=get_settings().room_inactivity_hours)
    with session_factory() as session:
        closed_count: int = _game_service(session).close_inactive_rooms(inactive_for)
    if closed_count:
        logger.info("Salles inactives fermées : %d", closed_count)


def _reschedule_rounds(session_factory: SessionFactory) -> None:
    """Un processus qui démarre n'a aucun timer : les échéances des tours en cours et des
    cooldowns sont relues en base et reprogrammées (une échéance passée pendant l'arrêt se
    déclenche tout de suite)."""
    try:
        with session_factory() as session:
            games: GameService = _game_service(session)
            deadlines: list[tuple[uuid.UUID, int, datetime]] = games.pending_round_deadlines()
            cooldown_ends: list[tuple[uuid.UUID, datetime]] = games.pending_cooldown_ends()
    except SQLAlchemyError:
        logger.warning("Timers des tours non reprogrammés : base injoignable", exc_info=True)
        return
    for game_id, round_number, ends_at in deadlines:
        round_timers.schedule(game_id, round_number, ends_at)
    for game_id, cooldown_ends_at in cooldown_ends:
        round_timers.schedule_cooldown_end(game_id, cooldown_ends_at)
    logger.info(
        "Timers reprogrammés au démarrage : %d tours, %d cooldowns",
        len(deadlines),
        len(cooldown_ends),
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Les dépendances ne sont pas injectées ici : la fabrique remplacée par les tests (sur l'API
    # montée sous /api), s'il y en a une, est reprise pour ne jamais toucher une autre base
    get_factory = api_app.dependency_overrides.get(get_session_factory, get_session_factory)
    session_factory: SessionFactory = get_factory()
    settings: Settings = get_settings()
    await run_in_threadpool(_reset_presence, session_factory)

    async def on_deadline(game_id: uuid.UUID, round_number: int) -> None:
        # La base est synchrone : la transition passe par le threadpool (realtime.md, §2.8)
        await run_in_threadpool(_end_round_on_timer, session_factory, game_id, round_number)

    async def on_cooldown_deadline(game_id: uuid.UUID) -> None:
        await run_in_threadpool(_end_cooldown_on_timer, session_factory, game_id)

    async def sweep_inactive_rooms() -> None:
        await run_in_threadpool(_close_inactive_rooms, session_factory)

    async def purge_templates() -> int:
        return await run_in_threadpool(purge_deleted_templates, session_factory, settings)

    async def purge_images() -> int:
        return await run_in_threadpool(
            purge_unused_images, session_factory, settings, create_image_storage(settings)
        )

    round_timers.start(asyncio.get_running_loop(), on_deadline, on_cooldown_deadline)
    await run_in_threadpool(_reschedule_rounds, session_factory)
    room_sweeper.start(settings.room_inactivity_sweep_minutes * 60, sweep_inactive_rooms)
    if settings.maintenance_enabled:
        nightly_scheduler.start(
            settings.maintenance_hour_utc,
            {"purge_deleted_templates": purge_templates, "purge_unused_images": purge_images},
        )
    yield
    await nightly_scheduler.stop()
    await room_sweeper.stop()
    await round_timers.stop()


# L'API : toutes ses routes, REST et canal temps réel, sont servies sous /api par l'application
# racine ci-dessous. Montée comme sous-application, elle garde des chemins sans /api dans son
# contrat (openapi.json, types du frontend) et dans les tests, qui l'appellent directement.
api_app = FastAPI(
    title="TierList API",
    description="Backend FastAPI de l'application TierList",
    version="0.5.0",
    # Toute route peut échouer de façon imprévue : la 500 générique figure dans le contrat
    responses={500: {"model": ErrorResponse, "description": messages.INTERNAL_ERROR}},
)
register_error_handlers(api_app)
api_app.include_router(auth.router)
api_app.include_router(templates.router)
api_app.include_router(images.router)
api_app.include_router(rooms.router)
api_app.include_router(room_channel.router)
api_app.include_router(results.router)
api_app.include_router(history.router)


def _openapi_with_room_messages() -> dict[str, Any]:
    """Contrat de l'API, augmenté des messages du canal temps réel : ils ne passent par aucune
    route REST, mais le frontend en génère les types (pnpm gen:api)."""
    if api_app.openapi_schema:
        return api_app.openapi_schema
    schema: dict[str, Any] = get_openapi(
        title=api_app.title,
        version=api_app.version,
        description=api_app.description,
        routes=api_app.routes,
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
    api_app.openapi_schema = schema
    return schema


api_app.openapi = _openapi_with_room_messages  # type: ignore[method-assign]


class HealthResponse(BaseModel):
    status: str
    # Version qui tourne (APP_RELEASE) : le déploiement vérifie que c'est bien la nouvelle
    release: str


# Sonde de vie : ne dépend pas de la base, pour qu'une panne de la base ne fasse pas
# redémarrer en boucle une application qui fonctionne (hébergeur).
@api_app.get("/health")
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", release=settings.app_release)


@api_app.get(
    "/health/db",
    responses={503: {"model": ErrorResponse, "description": messages.DATABASE_UNAVAILABLE}},
)
def health_db(
    session: Annotated[Session, Depends(get_db_session)], settings: SettingsDep
) -> HealthResponse:
    try:
        ping_database(session)
    except SQLAlchemyError as exc:
        logger.exception("Échec de la connexion à la base de données")
        raise AppHTTPException(
            status_code=503,
            code=ErrorCode.DATABASE_UNAVAILABLE,
            detail=messages.DATABASE_UNAVAILABLE,
        ) from exc
    return HealthResponse(status="ok", release=settings.app_release)


# Application racine, lancée par uvicorn (app.main:app) : l'API sous /api et, en production, le
# build du frontend sur la même origine (docs/technical/deployment.md)
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
# Erreurs HTTP au format de l'API (404 hors du build, /api seul) ; pas de second middleware
# d'erreurs : celui de api_app suffit, et chaque couche de middleware HTTP exécute la suite de la
# requête dans une tâche à part, ce qui décale la fin des requêtes de l'API
app.add_exception_handler(StarletteHTTPException, handle_http_exception)
app.mount(API_PREFIX, api_app)
_settings: Settings = get_settings()
if _settings.frontend_dist.is_dir():
    mount_frontend(app, _settings.frontend_dist)
