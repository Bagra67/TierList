from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.rooms import FREE_PLAN_MAX_PARTICIPANTS
from app.models.participant import Participant
from app.models.room import Room, RoomStatus
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


def fill_with_guests(client: TestClient, code: str, count: int) -> None:
    """Ajoute count invités (plus rapide que des comptes), depuis des navigateurs distincts."""
    for index in range(count):
        client.cookies.clear()
        assert join_as_guest(client, code, f"Guest{index}").status_code == 201
    client.cookies.clear()


def fill_the_room(client: TestClient, code: str) -> None:
    # La place du room admin compte : il reste FREE_PLAN_MAX_PARTICIPANTS - 1 places
    fill_with_guests(client, code, FREE_PLAN_MAX_PARTICIPANTS - 1)


def start_a_game(db_session: Session, code: str, late_arrivals_allowed: bool) -> None:
    # Une partie est en cours (posé par le démarrage, #91)
    room: Room = db_session.scalars(select(Room).where(Room.code == code)).one()
    room.status = RoomStatus.PLAYING
    room.late_arrivals_allowed = late_arrivals_allowed
    db_session.flush()


def assert_room_full(response: Response) -> None:
    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ROOM_FULL
    assert response.json()["params"] == {"max_participants": FREE_PLAN_MAX_PARTICIPANTS}


def assert_room_locked(response: Response) -> None:
    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ROOM_LOCKED


# --- Capacité -------------------------------------------------------------------------------


def test_the_room_admin_counts_and_the_room_fills_up_to_the_limit(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]

    fill_the_room(auth_client, code)

    participants: list[JsonObject] = auth_client.get(f"/rooms/{code}", headers=alice).json()[
        "participants"
    ]
    assert len(participants) == FREE_PLAN_MAX_PARTICIPANTS


def test_an_account_cannot_join_a_full_room(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    fill_the_room(auth_client, alice_room["code"])

    assert_room_full(join(auth_client, alice_room["code"], bob))


def test_a_guest_cannot_join_a_full_room(auth_client: TestClient, alice_room: JsonObject):
    fill_the_room(auth_client, alice_room["code"])

    assert_room_full(join_as_guest(auth_client, alice_room["code"], "Late"))


def test_an_expired_guest_seat_frees_a_place(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    fill_the_room(auth_client, code)
    expired: Participant = db_session.scalars(
        select(Participant).where(Participant.nickname == "Guest0")
    ).one()
    expired.guest_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response: Response = join(auth_client, code, bob)

    assert response.status_code == 200


def test_a_participant_comes_back_to_a_full_room(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    fill_with_guests(auth_client, code, FREE_PLAN_MAX_PARTICIPANTS - 2)

    response: Response = join(auth_client, code, bob)

    assert response.status_code == 200


# --- Verrou des arrivées --------------------------------------------------------------------


def test_newcomers_cannot_join_a_locked_room_during_a_game(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    start_a_game(db_session, code, late_arrivals_allowed=False)

    assert_room_locked(join(auth_client, code, bob))
    assert_room_locked(join_as_guest(auth_client, code, "Lou"))


def test_newcomers_join_during_a_game_when_arrivals_are_allowed(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    start_a_game(db_session, code, late_arrivals_allowed=True)

    assert join(auth_client, code, bob).status_code == 200


def test_the_lock_only_applies_during_a_game(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    auth_client.patch(
        f"/rooms/{code}/settings", json={"late_arrivals_allowed": False}, headers=alice
    )

    assert join(auth_client, code, bob).status_code == 200


def test_participants_come_back_to_a_locked_room(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    guest: JsonObject = join_as_guest(auth_client, code, "Lou").json()
    token: str = guest["guest_link"].split("#guest=", 1)[1]
    start_a_game(db_session, code, late_arrivals_allowed=False)

    assert join(auth_client, code, bob).status_code == 200
    assert auth_client.get(f"/rooms/{code}").status_code == 200
    restored: Response = auth_client.post(f"/rooms/{code}/guest-session", json={"token": token})
    assert restored.status_code == 200


def test_a_removed_participant_cannot_come_back_to_a_locked_room(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    joined: JsonObject = join(auth_client, code, bob).json()
    bob_id: str = next(p["id"] for p in joined["participants"] if p["display_name"] == "bob")
    start_a_game(db_session, code, late_arrivals_allowed=False)
    auth_client.delete(f"/rooms/{code}/participants/{bob_id}", headers=alice)

    assert_room_locked(join(auth_client, code, bob))
