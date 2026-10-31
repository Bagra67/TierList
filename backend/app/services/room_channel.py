"""Sockets temps réel ouverts par ce processus, et publication des événements des salles.

Étape 0 de docs/technical/realtime.md : un seul worker, tout en mémoire. Les services ne touchent
jamais un socket : ils publient par RoomEventPublisher, la seule abstraction introduite d'avance
(une diffusion entre plusieurs instances la remplacera).
"""

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


class RoomEventPublisher(Protocol):
    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        """Envoie l'événement à tous les sockets ouverts de la salle. Appelé après le commit."""
        ...

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        """Ferme les sockets du participant dans la salle, avec ce code et cette raison : sa place
        vient d'être supprimée. Appelé après le commit."""
        ...

    def close_room(self, room_id: uuid.UUID) -> None:
        """Ferme tous les sockets de la salle (CHANNEL_CLOSE_ROOM_CLOSED) : elle vient d'être
        fermée, donc supprimée. Appelé après le commit."""
        ...


class ConnectionRegistry:
    """Sockets ouverts de ce processus, par salle, avec le participant de chacun.

    Le registre n'est modifié que dans la boucle asyncio (route WebSocket). publish peut être
    appelé depuis le threadpool (routes REST synchrones) : l'envoi est alors confié à la boucle.
    """

    def __init__(self) -> None:
        self._sockets: dict[uuid.UUID, dict[WebSocket, uuid.UUID]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        # Départs en attente de la fin du délai de grâce, par participant
        self._pending_disconnects: dict[uuid.UUID, asyncio.Task[None]] = {}

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

    def schedule_disconnect(
        self,
        room_id: uuid.UUID,
        participant_id: uuid.UUID,
        delay_seconds: float,
        set_presence: Callable[[bool], Awaitable[None]],
    ) -> None:
        """Marque le participant déconnecté après le délai s'il n'a rouvert aucun socket."""

        async def disconnect_after_delay() -> None:
            try:
                await asyncio.sleep(delay_seconds)
                if self.is_connected(room_id, participant_id):
                    return
                await set_presence(False)
                # Revenu pendant cette écriture (l'annulation ne peut pas arrêter le thread qui
                # écrit) : son « connecté » a pu passer avant ce « déconnecté », on le rétablit
                if self.is_connected(room_id, participant_id):
                    await set_presence(True)
            finally:
                # Une tâche annulée puis remplacée ne doit pas retirer sa remplaçante
                if self._pending_disconnects.get(participant_id) is asyncio.current_task():
                    self._pending_disconnects.pop(participant_id, None)

        self.cancel_pending_disconnect(participant_id)
        self._pending_disconnects[participant_id] = asyncio.create_task(disconnect_after_delay())

    def cancel_pending_disconnect(self, participant_id: uuid.UUID) -> None:
        pending: asyncio.Task[None] | None = self._pending_disconnects.pop(participant_id, None)
        if pending is not None:
            pending.cancel()

    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        if self._loop is None or self._loop.is_closed():
            # Aucun socket n'a jamais été ouvert dans ce processus : personne à prévenir
            return
        message: str = _ROOM_EVENT_ADAPTER.dump_json(event).decode()
        self._loop.call_soon_threadsafe(self._schedule_broadcast, room_id, message)

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(
            self._schedule_close, room_id, participant_id, close_code, reason
        )

    def close_room(self, room_id: uuid.UUID) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._schedule_room_close, room_id)

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
        # Sa place n'existe plus : aucun départ à enregistrer après le délai de grâce
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
                # Socket déjà fermé côté client : sa route le retirera du registre
                logger.debug("Envoi impossible sur un socket fermé : room_id=%s", room_id)


# Le registre de ce processus : l'état global assumé de l'étape 0 (un seul worker)
room_connections: ConnectionRegistry = ConnectionRegistry()
