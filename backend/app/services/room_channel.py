import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic import TypeAdapter
from starlette.websockets import WebSocket

from app.constants.error_codes import ErrorCode
from app.constants.rooms import CHANNEL_CLOSE_ROOM_CLOSED
from app.schemas.room_events import RoomEvent

logger = logging.getLogger(__name__)

_ROOM_EVENT_ADAPTER: TypeAdapter[RoomEvent] = TypeAdapter(RoomEvent)


class PostCommitRoomPublisher(Protocol):
    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None: ...

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None: ...

    def close_room(self, room_id: uuid.UUID) -> None: ...


class ConnectionRegistry:
    def __init__(self) -> None:
        self._sockets: dict[uuid.UUID, dict[WebSocket, uuid.UUID]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending_disconnects: dict[uuid.UUID, asyncio.Task[None]] = {}

    def add(self, room_id: uuid.UUID, participant_id: uuid.UUID, websocket: WebSocket) -> bool:
        self._loop = asyncio.get_running_loop()
        room_sockets: dict[WebSocket, uuid.UUID] = self._sockets.setdefault(room_id, {})
        first: bool = participant_id not in room_sockets.values()
        room_sockets[websocket] = participant_id
        return first

    def remove(self, room_id: uuid.UUID, websocket: WebSocket) -> bool:
        room_sockets: dict[WebSocket, uuid.UUID] = self._sockets.get(room_id, {})
        participant_id: uuid.UUID | None = room_sockets.pop(websocket, None)
        if not room_sockets:
            self._sockets.pop(room_id, None)
        if participant_id is None:
            return False
        return not self.is_connected(room_id, participant_id)

    def is_connected(self, room_id: uuid.UUID, participant_id: uuid.UUID) -> bool:
        return participant_id in self._sockets.get(room_id, {}).values()

    def schedule_disconnect(
        self,
        room_id: uuid.UUID,
        participant_id: uuid.UUID,
        delay_seconds: float,
        set_presence: Callable[[bool], Awaitable[None]],
    ) -> None:

        async def disconnect_after_delay() -> None:
            try:
                await asyncio.sleep(delay_seconds)
                if self.is_connected(room_id, participant_id):
                    return
                await set_presence(False)
                if self.is_connected(room_id, participant_id):
                    await set_presence(True)
            finally:
                if self._pending_disconnects.get(participant_id) is asyncio.current_task():
                    self._pending_disconnects.pop(participant_id, None)

        self.cancel_pending_disconnect(participant_id)
        self._pending_disconnects[participant_id] = asyncio.create_task(disconnect_after_delay())

    def cancel_pending_disconnect(self, participant_id: uuid.UUID) -> None:
        pending: asyncio.Task[None] | None = self._pending_disconnects.pop(participant_id, None)
        if pending is not None:
            pending.cancel()

    def _loop_if_a_socket_can_be_open(self) -> asyncio.AbstractEventLoop | None:
        if self._loop is None or self._loop.is_closed():
            return None
        return self._loop

    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        loop: asyncio.AbstractEventLoop | None = self._loop_if_a_socket_can_be_open()
        if loop is None:
            return
        message: str = _ROOM_EVENT_ADAPTER.dump_json(event).decode()
        loop.call_soon_threadsafe(self._schedule_broadcast, room_id, message)

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        loop: asyncio.AbstractEventLoop | None = self._loop_if_a_socket_can_be_open()
        if loop is None:
            return
        loop.call_soon_threadsafe(self._schedule_close, room_id, participant_id, close_code, reason)

    def close_room(self, room_id: uuid.UUID) -> None:
        loop: asyncio.AbstractEventLoop | None = self._loop_if_a_socket_can_be_open()
        if loop is None:
            return
        loop.call_soon_threadsafe(self._schedule_room_close, room_id)

    def _schedule_room_close(self, room_id: uuid.UUID) -> None:
        participant_ids: set[uuid.UUID] = set(self._sockets.get(room_id, {}).values())
        for participant_id in participant_ids:
            self._schedule_close(
                room_id, participant_id, CHANNEL_CLOSE_ROOM_CLOSED, ErrorCode.ROOM_CLOSED
            )

    def _schedule_close(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        asyncio.create_task(self._close_participant(room_id, participant_id, close_code, reason))

    async def _close_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        self.cancel_pending_disconnect(participant_id)
        room_sockets: dict[WebSocket, uuid.UUID] = self._sockets.get(room_id, {})
        participant_sockets: list[WebSocket] = [
            websocket for websocket, owner_id in room_sockets.items() if owner_id == participant_id
        ]
        for websocket in participant_sockets:
            # Retiré du registre avant la fermeture : sa route ne programmera pas de départ, et il
            # ne reçoit plus les événements de la salle
            self.remove(room_id, websocket)
            try:
                await websocket.close(code=close_code, reason=reason)
            except RuntimeError, OSError:
                logger.debug("Fermeture impossible d'un socket déjà fermé : room_id=%s", room_id)

    def _schedule_broadcast(self, room_id: uuid.UUID, message: str) -> None:
        asyncio.create_task(self._broadcast(room_id, message))

    async def _broadcast(self, room_id: uuid.UUID, message: str) -> None:
        for websocket in list(self._sockets.get(room_id, {})):
            try:
                await websocket.send_text(message)
            except RuntimeError, OSError:
                logger.debug("Envoi impossible sur un socket fermé : room_id=%s", room_id)


room_connections: ConnectionRegistry = ConnectionRegistry()
