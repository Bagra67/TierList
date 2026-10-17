import asyncio
import threading
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, cast

from starlette.websockets import WebSocket

from app.constants.error_codes import ErrorCode
from app.schemas.room_events import RoomSettingsUpdatedEvent
from app.services.room_channel import ConnectionRegistry


class FakeSocket:
    """Socket factice : garde les messages reçus, ou échoue à l'envoi."""

    def __init__(self, failing: bool = False) -> None:
        self.messages: list[str] = []
        self.failing = failing
        # Code et raison de la fermeture demandée par le serveur
        self.closed_with: tuple[int, str] | None = None

    async def send_text(self, message: str) -> None:
        if self.failing:
            raise RuntimeError("socket closed")
        self.messages.append(message)

    async def close(self, code: int, reason: str) -> None:
        if self.failing:
            raise RuntimeError("socket closed")
        self.closed_with = (code, reason)


def as_websocket(socket: FakeSocket) -> WebSocket:
    """Le registre n'utilise que send_text et close : le faux socket suffit."""
    return cast(WebSocket, socket)


ROOM: uuid.UUID = uuid.uuid4()
OTHER_ROOM: uuid.UUID = uuid.uuid4()
ALICE: uuid.UUID = uuid.uuid4()
BOB: uuid.UUID = uuid.uuid4()


def run(scenario: Callable[[], Coroutine[Any, Any, None]]) -> None:
    asyncio.run(scenario())


def test_first_and_last_socket_of_a_participant():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        first_tab: FakeSocket = FakeSocket()
        second_tab: FakeSocket = FakeSocket()

        assert registry.add(ROOM, ALICE, as_websocket(first_tab)) is True
        assert registry.add(ROOM, ALICE, as_websocket(second_tab)) is False
        assert registry.remove(ROOM, as_websocket(second_tab)) is False
        assert registry.is_connected(ROOM, ALICE)
        assert registry.remove(ROOM, as_websocket(first_tab)) is True
        assert not registry.is_connected(ROOM, ALICE)

    run(scenario)


def test_a_publication_from_another_thread_reaches_only_the_room_sockets():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        in_room: FakeSocket = FakeSocket()
        elsewhere: FakeSocket = FakeSocket()
        registry.add(ROOM, ALICE, as_websocket(in_room))
        registry.add(OTHER_ROOM, BOB, as_websocket(elsewhere))

        # Comme une route REST synchrone, depuis le threadpool
        publisher: threading.Thread = threading.Thread(
            target=registry.publish, args=(ROOM, RoomSettingsUpdatedEvent(room_version=7))
        )
        publisher.start()
        publisher.join()
        await asyncio.sleep(0.05)

        assert in_room.messages == ['{"type":"room.settings_updated","room_version":7,"data":{}}']
        assert elsewhere.messages == []

    run(scenario)


def test_a_failing_socket_does_not_stop_the_others():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        closed: FakeSocket = FakeSocket(failing=True)
        open_socket: FakeSocket = FakeSocket()
        registry.add(ROOM, ALICE, as_websocket(closed))
        registry.add(ROOM, BOB, as_websocket(open_socket))

        registry.publish(ROOM, RoomSettingsUpdatedEvent(room_version=2))
        await asyncio.sleep(0.05)

        assert len(open_socket.messages) == 1

    run(scenario)


def test_coming_back_cancels_a_pending_disconnection():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        calls: list[bool] = []

        async def set_presence(connected: bool) -> None:
            calls.append(connected)

        registry.add(ROOM, ALICE, as_websocket(FakeSocket()))
        registry.schedule_disconnect(ROOM, ALICE, 0.05, set_presence)
        registry.cancel_pending_disconnect(ALICE)
        await asyncio.sleep(0.1)

        assert calls == []

    run(scenario)


def test_a_participant_back_during_the_departure_write_is_set_connected_again():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        calls: list[bool] = []

        async def set_presence(connected: bool) -> None:
            calls.append(connected)
            if not connected:
                # Le participant revient pendant que « déconnecté » s'écrit
                registry.add(ROOM, ALICE, as_websocket(FakeSocket()))

        registry.schedule_disconnect(ROOM, ALICE, 0, set_presence)
        await asyncio.sleep(0.05)

        assert calls == [False, True]

    run(scenario)


def test_a_replaced_pending_disconnection_does_not_remove_its_replacement():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        calls: list[bool] = []

        async def set_presence(connected: bool) -> None:
            calls.append(connected)

        registry.schedule_disconnect(ROOM, ALICE, 0.05, set_presence)
        # Le second départ remplace le premier, qui est annulé
        registry.schedule_disconnect(ROOM, ALICE, 0.1, set_presence)
        await asyncio.sleep(0.01)
        registry.cancel_pending_disconnect(ALICE)
        await asyncio.sleep(0.15)

        # Annuler a bien retiré la remplaçante : aucun départ n'a eu lieu
        assert calls == []

    run(scenario)


def test_disconnecting_a_participant_closes_only_their_sockets_in_that_room():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        first_tab: FakeSocket = FakeSocket()
        second_tab: FakeSocket = FakeSocket()
        other_participant: FakeSocket = FakeSocket()
        other_room: FakeSocket = FakeSocket()
        registry.add(ROOM, ALICE, as_websocket(first_tab))
        registry.add(ROOM, ALICE, as_websocket(second_tab))
        registry.add(ROOM, BOB, as_websocket(other_participant))
        registry.add(OTHER_ROOM, ALICE, as_websocket(other_room))

        # Comme une route REST synchrone, depuis le threadpool
        disconnecting: threading.Thread = threading.Thread(
            target=registry.disconnect_participant,
            args=(ROOM, ALICE, 4410, ErrorCode.REMOVED_FROM_ROOM),
        )
        disconnecting.start()
        disconnecting.join()
        await asyncio.sleep(0.05)

        assert first_tab.closed_with == (4410, "removed_from_room")
        assert second_tab.closed_with == (4410, "removed_from_room")
        assert other_participant.closed_with is None
        assert other_room.closed_with is None
        # Retirés du registre : ils ne reçoivent plus les événements de la salle
        assert not registry.is_connected(ROOM, ALICE)
        assert registry.is_connected(OTHER_ROOM, ALICE)

    run(scenario)


def test_disconnecting_cancels_the_pending_departure():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        calls: list[bool] = []

        async def set_presence(connected: bool) -> None:
            calls.append(connected)

        registry.add(ROOM, BOB, as_websocket(FakeSocket()))
        # Sa place est supprimée pendant le délai de grâce : plus de départ à écrire
        registry.schedule_disconnect(ROOM, ALICE, 0.05, set_presence)
        registry.disconnect_participant(ROOM, ALICE, 4411, ErrorCode.ROOM_BANNED)
        await asyncio.sleep(0.1)

        assert calls == []

    run(scenario)


def test_a_socket_already_closed_does_not_stop_the_disconnection():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        already_closed: FakeSocket = FakeSocket(failing=True)
        open_tab: FakeSocket = FakeSocket()
        registry.add(ROOM, ALICE, as_websocket(already_closed))
        registry.add(ROOM, ALICE, as_websocket(open_tab))

        registry.disconnect_participant(ROOM, ALICE, 4410, ErrorCode.REMOVED_FROM_ROOM)
        await asyncio.sleep(0.05)

        assert open_tab.closed_with == (4410, "removed_from_room")

    run(scenario)


def test_closing_a_room_closes_every_socket_of_that_room_only():
    async def scenario() -> None:
        registry: ConnectionRegistry = ConnectionRegistry()
        alice_tab: FakeSocket = FakeSocket()
        bob_tab: FakeSocket = FakeSocket()
        other_room: FakeSocket = FakeSocket()
        registry.add(ROOM, ALICE, as_websocket(alice_tab))
        registry.add(ROOM, BOB, as_websocket(bob_tab))
        registry.add(OTHER_ROOM, ALICE, as_websocket(other_room))

        # Comme une route REST synchrone, depuis le threadpool
        closing: threading.Thread = threading.Thread(target=registry.close_room, args=(ROOM,))
        closing.start()
        closing.join()
        await asyncio.sleep(0.05)

        assert alice_tab.closed_with == (4412, "room_closed")
        assert bob_tab.closed_with == (4412, "room_closed")
        assert other_room.closed_with is None
        assert not registry.is_connected(ROOM, ALICE)
        assert not registry.is_connected(ROOM, BOB)
        assert registry.is_connected(OTHER_ROOM, ALICE)

    run(scenario)
