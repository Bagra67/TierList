import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.rooms import CHANNEL_CLOSE_BANNED, CHANNEL_CLOSE_REMOVED
from app.models.enums import RoomStatus
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.schemas.room_events import ParticipantRemovedEvent
from tests.integration.conftest import RecordingRoomEventPublisher
from tests.integration.helpers import JsonObject, create_room, create_template, register

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice)
    return create_room(auth_client, alice, template_id)


def join(client: TestClient, code: str, headers: dict[str, str]) -> Response:
    return client.post(f"/rooms/{code}/join", headers=headers)


def join_as_guest(client: TestClient, code: str, nickname: str) -> Response:
    return client.post(f"/rooms/{code}/guests", json={"nickname": nickname})


def seat_id(room: JsonObject, display_name: str) -> str:
    return next(p["id"] for p in room["participants"] if p["display_name"] == display_name)


def remove(
    client: TestClient, code: str, participant_id: str, headers: dict[str, str], ban: bool = False
) -> Response:
    return client.delete(
        f"/rooms/{code}/participants/{participant_id}",
        params={"ban": str(ban).lower()},
        headers=headers,
    )


def display_names(room: JsonObject) -> list[str]:
    return [p["display_name"] for p in room["participants"]]


# --- Retirer un participant -----------------------------------------------------------------


def test_the_admin_removes_a_player(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    joined: JsonObject = join(auth_client, code, bob).json()
    bob_id: str = seat_id(joined, "bob")

    response: Response = remove(auth_client, code, bob_id, alice)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert display_names(body) == ["alice"]
    assert body["version"] == joined["version"] + 1
    assert body["bans"] == []
    removed: object = room_events.events[-1][1]
    assert isinstance(removed, ParticipantRemovedEvent)
    assert str(removed.data.participant_id) == bob_id
    assert removed.room_version == body["version"]
    assert room_events.disconnections == [(uuid.UUID(bob_id), CHANNEL_CLOSE_REMOVED)]
    # Il n'a plus de place : la salle lui est introuvable
    assert auth_client.get(f"/rooms/{code}", headers=bob).status_code == 404


def test_a_removed_player_can_join_again(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    bob_id: str = seat_id(join(auth_client, code, bob).json(), "bob")
    remove(auth_client, code, bob_id, alice)

    response: Response = join(auth_client, code, bob)

    assert response.status_code == 200
    assert display_names(response.json()) == ["alice", "bob"]


def test_the_admin_removes_a_guest_whose_link_stops_working(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    guest: JsonObject = join_as_guest(auth_client, code, "Lou").json()
    token: str = guest["guest_link"].split("#guest=", 1)[1]

    response: Response = remove(auth_client, code, seat_id(guest, "Lou"), alice)

    assert response.status_code == 200
    assert display_names(response.json()) == ["alice"]
    restored: Response = auth_client.post(f"/rooms/{code}/guest-session", json={"token": token})
    assert restored.status_code == 404
    assert restored.json()["code"] == ErrorCode.GUEST_LINK_INVALID


def test_the_admin_removes_a_participant_during_a_game(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    bob_id: str = seat_id(join(auth_client, code, bob).json(), "bob")
    # Une partie est en cours (posé par le démarrage, #91)
    db_session.scalars(select(Room).where(Room.code == code)).one().status = RoomStatus.PLAYING
    db_session.flush()

    response: Response = remove(auth_client, code, bob_id, alice)

    assert response.status_code == 200
    assert display_names(response.json()) == ["alice"]


def test_a_player_cannot_remove_anyone(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    joined: JsonObject = join(auth_client, code, bob).json()

    response: Response = remove(auth_client, code, seat_id(joined, "alice"), bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_removing_from_a_room_without_a_seat_is_not_found(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    response: Response = remove(auth_client, alice_room["code"], seat_id(alice_room, "alice"), bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_removing_an_unknown_participant_is_not_found(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = remove(auth_client, alice_room["code"], str(uuid.uuid4()), alice)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.PARTICIPANT_NOT_FOUND


def test_the_admin_cannot_remove_themselves(
    auth_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = remove(
        auth_client, alice_room["code"], seat_id(alice_room, "alice"), alice, ban=True
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_REMOVE_ROOM_ADMIN
    assert room_events.events == []
    assert room_events.disconnections == []


def test_removing_requires_authentication(auth_client: TestClient, alice_room: JsonObject):
    response: Response = auth_client.delete(
        f"/rooms/{alice_room['code']}/participants/{seat_id(alice_room, 'alice')}"
    )

    assert response.status_code == 401


# --- Bannir ---------------------------------------------------------------------------------


def test_a_banned_account_cannot_join_again(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    bob_id: str = seat_id(join(auth_client, code, bob).json(), "bob")

    banned: Response = remove(auth_client, code, bob_id, alice, ban=True)

    assert banned.status_code == 200
    assert display_names(banned.json()) == ["alice"]
    assert [(b["display_name"], b["is_guest"]) for b in banned.json()["bans"]] == [("bob", False)]
    assert room_events.disconnections == [(uuid.UUID(bob_id), CHANNEL_CLOSE_BANNED)]
    for typed_code in (code, code.lower()):
        refused: Response = join(auth_client, typed_code, bob)
        assert refused.status_code == 403
        assert refused.json()["code"] == ErrorCode.ROOM_BANNED


def test_a_banned_guest_cannot_join_again_from_the_same_browser(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    guest: JsonObject = join_as_guest(auth_client, code, "Lou").json()
    # Le client de test garde le cookie de l'invité, comme son navigateur
    remove(auth_client, code, seat_id(guest, "Lou"), alice, ban=True)

    refused: Response = join_as_guest(auth_client, code, "Lou2")

    assert refused.status_code == 403
    assert refused.json()["code"] == ErrorCode.ROOM_BANNED


def test_a_banned_guest_without_their_cookie_is_not_recognized(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    # Limite assumée (US-2.12) : sans compte ni cookie, rien ne reconnaît le banni
    code: str = alice_room["code"]
    guest: JsonObject = join_as_guest(auth_client, code, "Lou").json()
    remove(auth_client, code, seat_id(guest, "Lou"), alice, ban=True)
    auth_client.cookies.clear()

    response: Response = join_as_guest(auth_client, code, "Lou")

    assert response.status_code == 201


def test_the_ban_of_a_guest_keeps_their_token_fingerprint(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    guest: JsonObject = join_as_guest(auth_client, code, "Lou").json()

    banned: Response = remove(auth_client, code, seat_id(guest, "Lou"), alice, ban=True)

    assert [(b["display_name"], b["is_guest"]) for b in banned.json()["bans"]] == [("Lou", True)]
    room_ban: RoomBan = db_session.scalars(select(RoomBan)).one()
    assert room_ban.user_id is None
    assert room_ban.guest_token_hash is not None


def test_only_the_admin_sees_the_bans(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    carol: dict[str, str] = register(auth_client, "carol@example.com")
    bob_id: str = seat_id(join(auth_client, code, bob).json(), "bob")
    join(auth_client, code, carol)
    remove(auth_client, code, bob_id, alice, ban=True)

    assert len(auth_client.get(f"/rooms/{code}", headers=alice).json()["bans"]) == 1
    assert auth_client.get(f"/rooms/{code}", headers=carol).json()["bans"] == []


# --- Débannir -------------------------------------------------------------------------------


def test_an_unbanned_account_can_join_again(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    bob_id: str = seat_id(join(auth_client, code, bob).json(), "bob")
    ban_id: str = remove(auth_client, code, bob_id, alice, ban=True).json()["bans"][0]["id"]

    unbanned: Response = auth_client.delete(f"/rooms/{code}/bans/{ban_id}", headers=alice)

    assert unbanned.status_code == 200
    assert unbanned.json()["bans"] == []
    assert join(auth_client, code, bob).status_code == 200


def test_a_player_cannot_unban(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    carol: dict[str, str] = register(auth_client, "carol@example.com")
    carol_id: str = seat_id(join(auth_client, code, carol).json(), "carol")
    ban_id: str = remove(auth_client, code, carol_id, alice, ban=True).json()["bans"][0]["id"]
    join(auth_client, code, bob)

    response: Response = auth_client.delete(f"/rooms/{code}/bans/{ban_id}", headers=bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_unbanning_an_unknown_ban_is_not_found(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.delete(
        f"/rooms/{alice_room['code']}/bans/{uuid.uuid4()}", headers=alice
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.BAN_NOT_FOUND
