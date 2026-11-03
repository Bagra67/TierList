import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Cookie, WebSocket, WebSocketDisconnect, status
from pydantic import TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.types import Message
from starlette.websockets import WebSocketState

from app.api.dependencies import (
    PublisherDep,
    RegistryDep,
    RoundSchedulerDep,
    SettingsDep,
    ShortLivedSessionFactory,
    ShortLivedSessionFactoryDep,
    build_game_service,
)
from app.constants.error_codes import ErrorCode
from app.constants.rooms import (
    CHANNEL_CLOSE_HEARTBEAT_TIMEOUT,
    CHANNEL_CLOSE_INVALID_MESSAGE,
    CHANNEL_CLOSE_NOT_AUTHENTICATED,
    CHANNEL_CLOSE_ROOM_NOT_FOUND,
    GUEST_COOKIE,
)
from app.core.config import Settings
from app.exceptions.auth import InvalidAccessTokenError
from app.exceptions.rooms import ChannelClosedError, RoomNotFoundError
from app.models.participant import Participant
from app.schemas.room_events import AuthMessage, PingMessage, PongMessage, RoomClientMessage
from app.services.auth import AuthenticatedSession, AuthService
from app.services.games import GameService
from app.services.room_channel import ConnectionRegistry, PostCommitRoomPublisher
from app.services.rooms import RoomService, RoomViewer
from app.services.round_timers import RoundScheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rooms", tags=["rooms"])


_CLIENT_MESSAGE_ADAPTER: TypeAdapter[RoomClientMessage] = TypeAdapter(RoomClientMessage)
_PING: str = PingMessage().model_dump_json()


@dataclass(frozen=True)
class ChannelSeat:
    room_id: uuid.UUID
    participant_id: uuid.UUID


@router.websocket("/{code}/ws")
async def room_channel(
    websocket: WebSocket,
    code: str,
    settings: SettingsDep,
    session_factory: ShortLivedSessionFactoryDep,
    publisher: PublisherDep,
    registry: RegistryDep,
    scheduler: RoundSchedulerDep,
    guest_token: Annotated[str | None, Cookie(alias=GUEST_COOKIE)] = None,
) -> None:
    if websocket.headers.get("origin") != settings.app_origin:
        logger.warning("Canal refusé, origine inattendue : %s", websocket.headers.get("origin"))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    try:
        access_token: str | None = await _receive_auth(websocket, settings, guest_token)
        seat: ChannelSeat = await run_in_threadpool(
            _find_seat, session_factory, settings, publisher, code, access_token, guest_token
        )
        await _serve(websocket, seat, settings, session_factory, publisher, registry, scheduler)
    except ChannelClosedError as exc:
        await websocket.close(code=exc.close_code, reason=exc.reason)
    except WebSocketDisconnect:
        pass


async def _receive_auth(
    websocket: WebSocket, settings: Settings, guest_token: str | None
) -> str | None:
    try:
        text: str = await asyncio.wait_for(
            _receive_text(websocket), settings.room_auth_timeout_seconds
        )
    except TimeoutError as exc:
        raise ChannelClosedError(
            CHANNEL_CLOSE_NOT_AUTHENTICATED, ErrorCode.NOT_AUTHENTICATED
        ) from exc
    message: RoomClientMessage = _parse_client_message(text)
    if not isinstance(message, AuthMessage):
        raise ChannelClosedError(CHANNEL_CLOSE_INVALID_MESSAGE, ErrorCode.INVALID_MESSAGE)
    if message.access_token is None and guest_token is None:
        raise ChannelClosedError(CHANNEL_CLOSE_NOT_AUTHENTICATED, ErrorCode.NOT_AUTHENTICATED)
    return message.access_token


def _find_seat(
    session_factory: ShortLivedSessionFactory,
    settings: Settings,
    publisher: PostCommitRoomPublisher,
    code: str,
    access_token: str | None,
    guest_token: str | None,
) -> ChannelSeat:
    """Place du lecteur dans la salle. Comme en REST, un compte passe avant un cookie d'invité,
    et une salle inconnue ou sans place pour lui sont indiscernables (room_not_found)."""
    with session_factory() as session:
        viewer: RoomViewer = RoomViewer(user=None, guest_token=guest_token)
        if access_token is not None:
            authenticated: AuthenticatedSession | None
            try:
                authenticated = AuthService(session, settings).authenticate_access_token(
                    access_token
                )
            except InvalidAccessTokenError:
                authenticated = None
            if authenticated is None:
                raise ChannelClosedError(
                    CHANNEL_CLOSE_NOT_AUTHENTICATED, ErrorCode.NOT_AUTHENTICATED
                )
            viewer = RoomViewer(user=authenticated.user, guest_token=None)
        try:
            seat: Participant = RoomService(session, settings, publisher).seat_of(viewer, code)
        except RoomNotFoundError as exc:
            raise ChannelClosedError(
                CHANNEL_CLOSE_ROOM_NOT_FOUND, ErrorCode.ROOM_NOT_FOUND
            ) from exc
        return ChannelSeat(room_id=seat.room_id, participant_id=seat.id)


async def _serve(
    websocket: WebSocket,
    seat: ChannelSeat,
    settings: Settings,
    session_factory: ShortLivedSessionFactory,
    publisher: PostCommitRoomPublisher,
    registry: ConnectionRegistry,
    scheduler: RoundScheduler,
) -> None:

    async def set_presence(connected: bool) -> None:
        await run_in_threadpool(
            _set_presence, session_factory, settings, publisher, scheduler, seat, connected
        )

    first_socket: bool = registry.add(seat.room_id, seat.participant_id, websocket)
    registry.cancel_pending_disconnect(seat.participant_id)
    try:
        if first_socket:
            await set_presence(True)
        await _heartbeat(websocket, settings)
    finally:
        if registry.remove(seat.room_id, websocket):
            registry.schedule_disconnect(
                seat.room_id,
                seat.participant_id,
                settings.room_presence_grace_seconds,
                set_presence,
            )


def _set_presence(
    session_factory: ShortLivedSessionFactory,
    settings: Settings,
    publisher: PostCommitRoomPublisher,
    scheduler: RoundScheduler,
    seat: ChannelSeat,
    connected: bool,
) -> None:
    with session_factory() as session:
        games: GameService = build_game_service(session, settings, publisher, scheduler)
        games.set_presence(seat.participant_id, connected)


async def _heartbeat(websocket: WebSocket, settings: Settings) -> None:
    while True:
        try:
            text: str = await asyncio.wait_for(
                _receive_text(websocket), settings.room_heartbeat_interval_seconds
            )
        except TimeoutError:
            if _closed_by_registry(websocket):
                return
            await websocket.send_text(_PING)
            try:
                text = await asyncio.wait_for(
                    _receive_text(websocket), settings.room_heartbeat_timeout_seconds
                )
            except TimeoutError as exc:
                raise ChannelClosedError(
                    CHANNEL_CLOSE_HEARTBEAT_TIMEOUT, ErrorCode.HEARTBEAT_TIMEOUT
                ) from exc
        if not isinstance(_parse_client_message(text), PongMessage):
            raise ChannelClosedError(CHANNEL_CLOSE_INVALID_MESSAGE, ErrorCode.INVALID_MESSAGE)


def _closed_by_registry(websocket: WebSocket) -> bool:
    return websocket.application_state == WebSocketState.DISCONNECTED


async def _receive_text(websocket: WebSocket) -> str:
    message: Message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", status.WS_1000_NORMAL_CLOSURE))
    text: str | None = message.get("text")
    if text is None:
        raise ChannelClosedError(CHANNEL_CLOSE_INVALID_MESSAGE, ErrorCode.INVALID_MESSAGE)
    return text


def _parse_client_message(text: str) -> RoomClientMessage:
    try:
        return _CLIENT_MESSAGE_ADAPTER.validate_json(text)
    except ValidationError as exc:
        raise ChannelClosedError(CHANNEL_CLOSE_INVALID_MESSAGE, ErrorCode.INVALID_MESSAGE) from exc
