"""Sockets temps réel ouverts par ce processus, et publication des événements des salles.

Étape 0 de docs/technical/realtime.md : un seul worker, tout en mémoire. Les services ne touchent
jamais un socket : ils publient par RoomEventPublisher, la seule abstraction introduite d'avance
(une diffusion entre plusieurs instances la remplacera).
"""

import asyncio
import logging
import uuid
from typing import Protocol

from pydantic import TypeAdapter
from starlette.websockets import WebSocket

from app.schemas.room_events import RoomEvent

logger = logging.getLogger(__name__)

_ROOM_EVENT_ADAPTER: TypeAdapter[RoomEvent] = TypeAdapter(RoomEvent)


class RoomEventPublisher(Protocol):
    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        """Envoie l'événement à tous les sockets ouverts de la salle. Appelé après le commit."""
        ...


class ConnectionRegistry:
    """Sockets ouverts de ce processus, par salle, avec le participant de chacun.

    Le registre n'est modifié que dans la boucle asyncio (route WebSocket). publish peut être
    appelé depuis le threadpool (routes REST synchrones) : l'envoi est alors confié à la boucle.
    """

    def __init__(self) -> None:
        self._sockets: dict[uuid.UUID, dict[WebSocket, uuid.UUID]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def add(self, room_id: uuid.UUID, participant_id: uuid.UUID, websocket: WebSocket) -> bool:
        """Enregistre le socket ; True si c'est le premier socket ouvert de ce participant."""
        self._loop = asyncio.get_running_loop()
        room_sockets: dict[WebSocket, uuid.UUID] = self._sockets.setdefault(room_id, {})
        first: bool = participant_id not in room_sockets.values()
        room_sockets[websocket] = participant_id
        return first

    def remove(self, room_id: uuid.UUID, websocket: WebSocket) -> bool:
        """Retire le socket ; True si son participant n'a plus aucun socket ouvert."""
        room_sockets: dict[WebSocket, uuid.UUID] = self._sockets.get(room_id, {})
        participant_id: uuid.UUID | None = room_sockets.pop(websocket, None)
        if not room_sockets:
            self._sockets.pop(room_id, None)
        if participant_id is None:
            return False
        return not self.is_connected(room_id, participant_id)

    def is_connected(self, room_id: uuid.UUID, participant_id: uuid.UUID) -> bool:
        return participant_id in self._sockets.get(room_id, {}).values()

    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        if self._loop is None or self._loop.is_closed():
            # Aucun socket n'a jamais été ouvert dans ce processus : personne à prévenir
            return
        message: str = _ROOM_EVENT_ADAPTER.dump_json(event).decode()
        self._loop.call_soon_threadsafe(self._schedule_broadcast, room_id, message)

    def _schedule_broadcast(self, room_id: uuid.UUID, message: str) -> None:
        asyncio.create_task(self._broadcast(room_id, message))

    async def _broadcast(self, room_id: uuid.UUID, message: str) -> None:
        for websocket in list(self._sockets.get(room_id, {})):
            try:
                await websocket.send_text(message)
            except (RuntimeError, OSError):
                # Socket déjà fermé côté client : sa route le retirera du registre
                logger.debug("Envoi impossible sur un socket fermé : room_id=%s", room_id)


# Le registre de ce processus : l'état global assumé de l'étape 0 (un seul worker)
room_connections: ConnectionRegistry = ConnectionRegistry()
