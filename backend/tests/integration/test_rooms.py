import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.rooms import (
    COOLDOWN_SECONDS_MAX,
    COOLDOWN_SECONDS_MIN,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    ROOM_CODE_MAX_ATTEMPTS,
    TIMER_SECONDS_MAX,
    TIMER_SECONDS_MIN,
)
from app.core.config import get_settings
from app.models.enums import RoomStatus
from app.models.participant import Participant
from app.models.room import Room
from app.models.template import Template
from app.models.user import User
from app.schemas.room_events import ParticipantJoinedEvent, RoomEvent
from app.services import rooms as room_service_module
from app.services.rooms import RoomService
from tests.integration.conftest import RecordingRoomEventPublisher
from tests.integration.helpers import JsonObject, create_room, create_template, register

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


def user_with_email(db_session: Session, email: str) -> User:
    return db_session.scalars(select(User).where(User.email == email)).one()


@pytest.fixture
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice)
    return create_room(auth_client, alice, template_id)


def stored_room(db_session: Session, code: str) -> Room:
    return db_session.scalars(select(Room).where(Room.code == code)).one()


def forced_room_codes(monkeypatch: pytest.MonkeyPatch, codes: list[str]) -> None:
    """Le générateur de codes renvoie ces codes, dans l'ordre."""
    remaining_codes: Iterator[str] = iter(codes)
    monkeypatch.setattr(room_service_module, "generate_room_code", lambda: next(remaining_codes))


# --- Création -------------------------------------------------------------------------------


def test_create_room_makes_the_creator_its_admin_with_the_default_settings(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)

    response: Response = auth_client.post(
        "/rooms", json={"template_id": template_id}, headers=alice
    )

    assert response.status_code == 201
    body: JsonObject = response.json()
    code: str = body["code"]
    assert len(code) == ROOM_CODE_LENGTH
    assert set(code) <= set(ROOM_CODE_ALPHABET)
    assert body["link"] == f"{get_settings().frontend_base_url}/r/{code}"
    assert body["status"] == "open"
    assert body["template"] == {"id": template_id, "name": "Food"}
    assert body["settings"] == {
        "item_order": "template",
        "auto_advance": "none",
        "timer_seconds": get_settings().room_default_timer_seconds,
        "cooldown_seconds": get_settings().room_default_cooldown_seconds,
        "admin_plays": True,
        "late_arrivals_allowed": True,
    }
    assert [(p["display_name"], p["is_admin"]) for p in body["participants"]] == [("alice", True)]
    assert body["is_admin"] is True


def test_default_durations_are_settings(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    override_settings: Callable[..., None],
):
    template_id: str = create_template(auth_client, db_session, alice)
    override_settings(room_default_timer_seconds=45, room_default_cooldown_seconds=120)

    body: JsonObject = create_room(auth_client, alice, template_id)

    assert body["settings"]["timer_seconds"] == 45
    assert body["settings"]["cooldown_seconds"] == 120


def test_create_room_from_a_template_without_tiles_is_refused(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice, tile_count=0)

    response: Response = auth_client.post(
        "/rooms", json={"template_id": template_id}, headers=alice
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HAS_NO_TILES
    assert db_session.scalars(select(Room)).all() == []


def test_create_room_from_the_template_of_another_user_is_not_found(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)

    response: Response = auth_client.post("/rooms", json={"template_id": template_id}, headers=bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_create_room_from_a_deleted_template_is_not_found(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)
    assert auth_client.delete(f"/templates/{template_id}", headers=alice).status_code == 204

    response: Response = auth_client.post(
        "/rooms", json={"template_id": template_id}, headers=alice
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_create_room_requires_authentication(auth_client: TestClient):
    response: Response = auth_client.post("/rooms", json={"template_id": str(uuid.uuid4())})

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


def test_a_taken_code_is_drawn_again(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    template_id: str = create_template(auth_client, db_session, alice)
    forced_room_codes(monkeypatch, ["AAAAAA", "AAAAAA", "BBBBBB"])

    first_room: JsonObject = create_room(auth_client, alice, template_id)
    second_room: JsonObject = create_room(auth_client, alice, template_id)

    assert first_room["code"] == "AAAAAA"
    assert second_room["code"] == "BBBBBB"
    assert len(db_session.scalars(select(Room)).all()) == 2


def test_creation_gives_up_when_no_code_is_free(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    template_id: str = create_template(auth_client, db_session, alice)
    forced_room_codes(monkeypatch, ["AAAAAA"] * (ROOM_CODE_MAX_ATTEMPTS + 1))
    create_room(auth_client, alice, template_id)
    service: RoomService = RoomService(db_session, get_settings(), RecordingRoomEventPublisher())

    with pytest.raises(RuntimeError):
        service.create(user_with_email(db_session, "alice@example.com"), uuid.UUID(template_id))
    assert len(db_session.scalars(select(Room)).all()) == 1


# --- Lecture --------------------------------------------------------------------------------


def test_the_admin_reads_the_room_by_its_code_in_any_case(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.get(f"/rooms/{alice_room['code'].lower()}", headers=alice)

    assert response.status_code == 200
    assert response.json() == alice_room


def test_a_room_is_not_found_for_a_user_without_a_seat(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.get(f"/rooms/{alice_room['code']}", headers=bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_an_unknown_code_is_not_found(auth_client: TestClient, alice: dict[str, str]):
    response: Response = auth_client.get("/rooms/ZZZZZZ", headers=alice)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_a_player_sees_the_room_without_being_its_admin(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    room: Room = stored_room(db_session, alice_room["code"])
    db_session.add(
        Participant(room_id=room.id, user_id=user_with_email(db_session, "bob@example.com").id)
    )
    db_session.flush()

    response: Response = auth_client.get(f"/rooms/{alice_room['code']}", headers=bob)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["is_admin"] is False
    assert [(p["display_name"], p["is_admin"]) for p in body["participants"]] == [
        ("alice", True),
        ("bob", False),
    ]


def test_each_reader_sees_their_own_seat_marked_as_you(
    auth_client: TestClient, bob: dict[str, str], alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    auth_client.post(f"/rooms/{code}/join", headers=bob)

    seen_by_alice: JsonObject = auth_client.get(f"/rooms/{code}", headers=alice).json()
    seen_by_bob: JsonObject = auth_client.get(f"/rooms/{code}", headers=bob).json()

    assert [(p["display_name"], p["is_you"]) for p in seen_by_alice["participants"]] == [
        ("alice", True),
        ("bob", False),
    ]
    assert [(p["display_name"], p["is_you"]) for p in seen_by_bob["participants"]] == [
        ("alice", False),
        ("bob", True),
    ]


# --- Rejoindre -------------------------------------------------------------------------------


def test_a_user_joins_a_room_as_a_player(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["is_admin"] is False
    assert [(p["display_name"], p["is_admin"]) for p in body["participants"]] == [
        ("alice", True),
        ("bob", False),
    ]
    # Sa place lui donne ensuite accès à la salle
    assert auth_client.get(f"/rooms/{alice_room['code']}", headers=bob).status_code == 200


def test_joining_again_gives_back_the_same_seat(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    first: Response = auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob)
    second: Response = auth_client.post(f"/rooms/{alice_room['code'].lower()}/join", headers=bob)

    assert second.status_code == 200
    assert second.json()["participants"] == first.json()["participants"]
    assert len(db_session.scalars(select(Participant)).all()) == 2


def test_the_admin_keeps_their_seat_when_joining(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/join", headers=alice)

    assert response.status_code == 200
    assert response.json() == alice_room


def test_joining_an_unknown_code_is_not_found(auth_client: TestClient, bob: dict[str, str]):
    response: Response = auth_client.post("/rooms/ZZZZZZ/join", headers=bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_joining_requires_authentication(auth_client: TestClient, alice_room: JsonObject):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/join")

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


# --- Événements temps réel ---------------------------------------------------------------


def test_joining_publishes_the_new_participant_with_the_next_version(
    auth_client: TestClient,
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob)

    body: JsonObject = response.json()
    assert body["version"] == alice_room["version"] + 1
    bob_seat: JsonObject = body["participants"][1]
    assert bob_seat["connected"] is False
    assert room_events.types() == ["participant.joined"]
    event: RoomEvent = room_events.events[0][1]
    assert isinstance(event, ParticipantJoinedEvent)
    assert event.room_version == body["version"]
    assert str(event.data.participant_id) == bob_seat["id"]


def test_joining_again_publishes_nothing(
    auth_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/join", headers=alice)

    assert response.json()["version"] == alice_room["version"]
    assert room_events.events == []


def test_changing_the_settings_publishes_them(
    auth_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    settings_url: str = f"/rooms/{alice_room['code']}/settings"

    changed: Response = auth_client.patch(settings_url, json={"admin_plays": False}, headers=alice)
    unchanged: Response = auth_client.patch(settings_url, json={}, headers=alice)

    assert changed.json()["version"] == alice_room["version"] + 1
    assert unchanged.json()["version"] == changed.json()["version"]
    # Une modification vide ne publie rien
    assert room_events.types() == ["room.settings_updated"]
    assert room_events.events[0][1].room_version == changed.json()["version"]


# --- Réglages -------------------------------------------------------------------------------


def test_the_admin_changes_some_settings(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings",
        json={"item_order": "random", "auto_advance": "timer", "timer_seconds": 20},
        headers=alice,
    )

    assert response.status_code == 200
    assert response.json()["settings"] == {
        **alice_room["settings"],
        "item_order": "random",
        "auto_advance": "timer",
        "timer_seconds": 20,
    }


def test_an_empty_settings_change_changes_nothing(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={"admin_plays": None}, headers=alice
    )

    assert response.status_code == 200
    assert response.json()["settings"] == alice_room["settings"]


@pytest.mark.parametrize(
    ("field", "value", "error_code", "param", "bound"),
    [
        ("timer_seconds", TIMER_SECONDS_MIN - 1, "greater_than_equal", "ge", TIMER_SECONDS_MIN),
        ("timer_seconds", TIMER_SECONDS_MAX + 1, "less_than_equal", "le", TIMER_SECONDS_MAX),
        (
            "cooldown_seconds",
            COOLDOWN_SECONDS_MIN - 1,
            "greater_than_equal",
            "ge",
            COOLDOWN_SECONDS_MIN,
        ),
        (
            "cooldown_seconds",
            COOLDOWN_SECONDS_MAX + 1,
            "less_than_equal",
            "le",
            COOLDOWN_SECONDS_MAX,
        ),
    ],
)
def test_durations_out_of_bounds_are_refused_with_the_bound(
    auth_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    field: str,
    value: int,
    error_code: str,
    param: str,
    bound: int,
):
    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={field: value}, headers=alice
    )

    assert response.status_code == 422
    body: JsonObject = response.json()
    assert body["code"] == ErrorCode.VALIDATION_ERROR
    assert body["errors"][0]["field"] == f"body.{field}"
    assert body["errors"][0]["code"] == error_code
    assert body["errors"][0]["params"] == {param: bound}


def test_an_unknown_setting_value_is_refused(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={"item_order": "alphabetical"}, headers=alice
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "body.item_order"


def test_a_player_cannot_change_the_settings(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    room: Room = stored_room(db_session, alice_room["code"])
    db_session.add(
        Participant(room_id=room.id, user_id=user_with_email(db_session, "bob@example.com").id)
    )
    db_session.flush()

    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={"admin_plays": False}, headers=bob
    )

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_a_user_without_a_seat_cannot_change_the_settings(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    response: Response = auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={"admin_plays": False}, headers=bob
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_settings_are_locked_during_a_game_except_late_arrivals(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    # Une partie est en cours (posé par le démarrage, #91)
    stored_room(db_session, alice_room["code"]).status = RoomStatus.PLAYING
    db_session.flush()
    settings_url: str = f"/rooms/{alice_room['code']}/settings"

    locked: Response = auth_client.patch(
        settings_url, json={"late_arrivals_allowed": False, "admin_plays": False}, headers=alice
    )
    allowed: Response = auth_client.patch(
        settings_url, json={"late_arrivals_allowed": False}, headers=alice
    )

    assert locked.status_code == 409
    assert locked.json()["code"] == ErrorCode.ROOM_SETTINGS_LOCKED
    assert allowed.status_code == 200
    assert allowed.json()["settings"]["late_arrivals_allowed"] is False
    assert allowed.json()["settings"]["admin_plays"] is True


# --- Suppressions ---------------------------------------------------------------------------


def test_purging_the_template_keeps_the_room_without_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    # Ce que fait la purge des templates supprimés (suppression définitive)
    db_session.execute(
        delete(Template).where(Template.id == uuid.UUID(alice_room["template"]["id"]))
    )
    db_session.expire_all()

    response: Response = auth_client.get(f"/rooms/{alice_room['code']}", headers=alice)

    assert response.status_code == 200
    assert response.json()["template"] is None


def test_deleting_the_admin_account_deletes_their_rooms(
    db_session: Session, alice_room: JsonObject
):
    db_session.delete(user_with_email(db_session, "alice@example.com"))
    db_session.flush()

    assert db_session.scalars(select(Room)).all() == []
    assert db_session.scalars(select(Participant)).all() == []
