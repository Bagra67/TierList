import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.testclient import WebSocketTestSession

from app.constants.error_codes import ErrorCode
from app.constants.rooms import (
    CHANNEL_CLOSE_HEARTBEAT_TIMEOUT,
    CHANNEL_CLOSE_INVALID_MESSAGE,
    CHANNEL_CLOSE_NOT_AUTHENTICATED,
    CHANNEL_CLOSE_ROOM_NOT_FOUND,
)
from tests.integration.helpers import JsonObject, create_room, create_template, register

pytestmark = pytest.mark.integration

# Origine de l'application dans les tests (FRONTEND_BASE_URL par défaut)
APP_ORIGIN: dict[str, str] = {"origin": "http://localhost:5173"}


@pytest.fixture
def channel_client(
    auth_client: TestClient, override_settings: Callable[..., None]
) -> Iterator[TestClient]:
    """Client ouvert une seule fois : sockets et requêtes REST partagent la même boucle, comme dans
    le serveur. Le délai de grâce est long par défaut : un socket fermé en fin de test laisse un
    départ en attente, annulé avec la boucle, au lieu d'écrire en base pendant le nettoyage (la
    session du test est partagée entre threads). Les tests de départ le raccourcissent pour Bob,
    après la connexion d'Alice, puis attendent l'événement avant de continuer."""
    override_settings(room_auth_timeout_seconds=1, room_presence_grace_seconds=30)
    with auth_client:
        yield auth_client


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    return create_room(auth_client, alice, create_template(auth_client, db_session, alice))


def channel(client: TestClient, code: str, origin: dict[str, str] = APP_ORIGIN) -> Any:
    return client.websocket_connect(f"/rooms/{code}/ws", headers=origin)


def access_token(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def authenticate(socket: WebSocketTestSession, headers: dict[str, str] | None) -> None:
    """Premier message : le token d'un compte, ou rien pour un invité (reconnu par son cookie)."""
    token: str | None = access_token(headers) if headers is not None else None
    socket.send_json({"type": "auth", "access_token": token})


def next_event(socket: WebSocketTestSession) -> JsonObject:
    """Prochain événement de la salle, sans les battements de cœur."""
    while True:
        message: JsonObject = socket.receive_json()
        if message["type"] != "ping":
            return message


def assert_closed_with(socket: WebSocketTestSession, close_code: int, reason: str) -> None:
    with pytest.raises(WebSocketDisconnect) as closed:
        socket.receive_json()
    assert closed.value.code == close_code
    assert closed.value.reason == reason


def participant(room: JsonObject, name: str) -> JsonObject:
    return next(p for p in room["participants"] if p["display_name"] == name)


# --- Connexion et présence ------------------------------------------------------------------


def test_an_account_opens_the_channel_and_becomes_present(
    channel_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    with channel(channel_client, code) as socket:
        authenticate(socket, alice)

        event: JsonObject = next_event(socket)

        room: JsonObject = channel_client.get(f"/rooms/{code}", headers=alice).json()
        assert event == {
            "type": "participant.presence",
            "room_version": room["version"],
            "data": {"participant_id": participant(room, "alice")["id"], "connected": True},
        }
        assert room["version"] == alice_room["version"] + 1
        assert participant(room, "alice")["connected"] is True


def test_a_guest_is_recognised_by_the_cookie(
    channel_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    channel_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"})

    with channel(channel_client, code) as socket:
        authenticate(socket, None)
        event: JsonObject = next_event(socket)
        room: JsonObject = channel_client.get(f"/rooms/{code}", headers=alice).json()

    assert event["type"] == "participant.presence"
    assert event["data"]["participant_id"] == participant(room, "Lou")["id"]


def test_the_room_sees_a_player_arrive_and_leave(
    channel_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    override_settings: Callable[..., None],
):
    code: str = alice_room["code"]
    bob: dict[str, str] = register(channel_client, "bob@example.com")
    with channel(channel_client, code) as alice_socket:
        authenticate(alice_socket, alice)
        next_event(alice_socket)
        override_settings(room_presence_grace_seconds=0)

        # Bob rejoint par REST : l'événement part du threadpool vers la boucle des sockets
        channel_client.post(f"/rooms/{code}/join", headers=bob)
        joined: JsonObject = next_event(alice_socket)
        with channel(channel_client, code) as bob_socket:
            authenticate(bob_socket, bob)
            connected: JsonObject = next_event(alice_socket)
            next_event(bob_socket)
        disconnected: JsonObject = next_event(alice_socket)
        room: JsonObject = channel_client.get(f"/rooms/{code}", headers=alice).json()

    bob_id: str = participant(room, "bob")["id"]
    assert joined["type"] == "participant.joined"
    assert joined["data"] == {"participant_id": bob_id}
    assert connected["data"] == {"participant_id": bob_id, "connected": True}
    assert disconnected["data"] == {"participant_id": bob_id, "connected": False}
    # Chaque événement suit le précédent : les versions se suivent sans trou
    assert [joined["room_version"], connected["room_version"], disconnected["room_version"]] == [
        joined["room_version"],
        joined["room_version"] + 1,
        joined["room_version"] + 2,
    ]
    assert participant(room, "bob")["connected"] is False


def test_a_second_tab_keeps_the_participant_connected(
    channel_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    override_settings: Callable[..., None],
):
    code: str = alice_room["code"]
    bob: dict[str, str] = register(channel_client, "bob@example.com")
    channel_client.post(f"/rooms/{code}/join", headers=bob)
    with channel(channel_client, code) as alice_socket:
        authenticate(alice_socket, alice)
        next_event(alice_socket)
        override_settings(room_presence_grace_seconds=0)
        with channel(channel_client, code) as first_tab:
            authenticate(first_tab, bob)
            next_event(alice_socket)
            with channel(channel_client, code) as second_tab:
                authenticate(second_tab, bob)
                # Le second onglet ne change rien : pas d'événement de présence
            # Le second onglet est fermé, le premier reste : Bob reste connecté. Le prochain
            # événement est donc le changement de réglages, pas un départ
            channel_client.patch(
                f"/rooms/{code}/settings", json={"admin_plays": False}, headers=alice
            )
            assert next_event(alice_socket)["type"] == "room.settings_updated"
        assert next_event(alice_socket)["data"]["connected"] is False


def test_coming_back_within_the_grace_delay_keeps_the_participant_connected(
    channel_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    override_settings: Callable[..., None],
):
    code: str = alice_room["code"]
    bob: dict[str, str] = register(channel_client, "bob@example.com")
    channel_client.post(f"/rooms/{code}/join", headers=bob)
    with channel(channel_client, code) as alice_socket:
        authenticate(alice_socket, alice)
        next_event(alice_socket)
        override_settings(room_presence_grace_seconds=0.5)
        with channel(channel_client, code) as bob_socket:
            authenticate(bob_socket, bob)
            next_event(alice_socket)
        # Rechargement de la page : Bob revient avant la fin du délai de grâce
        with channel(channel_client, code) as bob_socket:
            authenticate(bob_socket, bob)
            time.sleep(0.8)
            channel_client.patch(
                f"/rooms/{code}/settings", json={"admin_plays": False}, headers=alice
            )
            assert next_event(alice_socket)["type"] == "room.settings_updated"
            room: JsonObject = channel_client.get(f"/rooms/{code}", headers=alice).json()
            assert participant(room, "bob")["connected"] is True


# --- Refus et fermetures ------------------------------------------------------------------


def test_the_channel_closes_without_authentication(
    channel_client: TestClient, alice_room: JsonObject, override_settings: Callable[..., None]
):
    override_settings(room_auth_timeout_seconds=0.2)
    with channel(channel_client, alice_room["code"]) as socket:
        assert_closed_with(socket, CHANNEL_CLOSE_NOT_AUTHENTICATED, ErrorCode.NOT_AUTHENTICATED)


@pytest.mark.parametrize("token", ["not-a-token", None])
def test_a_wrong_token_or_no_cookie_is_not_authenticated(
    channel_client: TestClient, alice_room: JsonObject, token: str | None
):
    with channel(channel_client, alice_room["code"]) as socket:
        socket.send_json({"type": "auth", "access_token": token})
        assert_closed_with(socket, CHANNEL_CLOSE_NOT_AUTHENTICATED, ErrorCode.NOT_AUTHENTICATED)


def test_a_user_without_a_seat_cannot_open_the_channel(
    channel_client: TestClient, alice_room: JsonObject
):
    bob: dict[str, str] = register(channel_client, "bob@example.com")
    with channel(channel_client, alice_room["code"]) as socket:
        authenticate(socket, bob)
        assert_closed_with(socket, CHANNEL_CLOSE_ROOM_NOT_FOUND, ErrorCode.ROOM_NOT_FOUND)


def test_an_unknown_room_cannot_be_followed(channel_client: TestClient, alice: dict[str, str]):
    with channel(channel_client, "ZZZZZZ") as socket:
        authenticate(socket, alice)
        assert_closed_with(socket, CHANNEL_CLOSE_ROOM_NOT_FOUND, ErrorCode.ROOM_NOT_FOUND)


def test_another_origin_is_refused(channel_client: TestClient, alice_room: JsonObject):
    with (
        pytest.raises(WebSocketDisconnect),
        channel(channel_client, alice_room["code"], {"origin": "https://evil.example"}),
    ):
        pass


def test_an_unexpected_message_closes_the_channel(
    channel_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    with channel(channel_client, alice_room["code"]) as socket:
        authenticate(socket, alice)
        next_event(socket)

        socket.send_json({"type": "auth", "access_token": access_token(alice)})

        assert_closed_with(socket, CHANNEL_CLOSE_INVALID_MESSAGE, ErrorCode.INVALID_MESSAGE)


def test_the_server_pings_and_closes_a_silent_client(
    channel_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    override_settings: Callable[..., None],
):
    override_settings(
        room_heartbeat_interval_seconds=0.2,
        room_heartbeat_timeout_seconds=0.3,
        room_auth_timeout_seconds=1,
    )
    with channel(channel_client, alice_room["code"]) as socket:
        authenticate(socket, alice)
        next_event(socket)

        # Un pong garde le canal ouvert : un nouveau ping suit
        assert socket.receive_json() == {"type": "ping"}
        socket.send_json({"type": "pong"})
        assert socket.receive_json() == {"type": "ping"}

        # Sans pong, le serveur ferme le canal
        assert_closed_with(socket, CHANNEL_CLOSE_HEARTBEAT_TIMEOUT, ErrorCode.HEARTBEAT_TIMEOUT)
