from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.rooms import GUEST_COOKIE
from app.core.config import get_settings
from app.models.participant import Participant
from app.models.room import Room
from app.services.rooms import RoomService
from tests.integration.helpers import JsonObject, create_room, create_template, register

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice)
    return create_room(auth_client, alice, template_id)


def join_as_guest(client: TestClient, code: str, nickname: str) -> Response:
    return client.post(f"/rooms/{code}/guests", json={"nickname": nickname})


def token_of(guest_link: str) -> str:
    """Jeton porté par le fragment du lien perso (#guest=<jeton>)."""
    return guest_link.split("#guest=", 1)[1]


def guest_seat(db_session: Session, nickname: str) -> Participant:
    return db_session.scalars(select(Participant).where(Participant.nickname == nickname)).one()


# --- Rejoindre en invité --------------------------------------------------------------------


def test_a_guest_joins_with_a_nickname_and_gets_a_cookie_and_a_personal_link(
    auth_client: TestClient, alice_room: JsonObject
):
    code: str = alice_room["code"]

    response: Response = join_as_guest(auth_client, code, "  Lou ")

    assert response.status_code == 201
    body: JsonObject = response.json()
    assert body["guest_link"].startswith(f"{alice_room['link']}#guest=")
    assert body["is_admin"] is False
    assert [(p["display_name"], p["is_admin"], p["is_guest"]) for p in body["participants"]] == [
        ("alice", True, False),
        ("Lou", False, True),
    ]
    expires_at: datetime = datetime.fromisoformat(body["guest_link_expires_at"])
    expected_expiry: datetime = datetime.now(UTC) + timedelta(
        days=get_settings().guest_link_ttl_days
    )
    assert abs(expires_at - expected_expiry) < timedelta(minutes=1)
    cookie: str = response.headers["set-cookie"]
    assert cookie.startswith(f"{GUEST_COOKIE}={token_of(body['guest_link'])};")
    assert f"Path=/rooms/{code}" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie


def test_the_cookie_gives_access_to_the_room(auth_client: TestClient, alice_room: JsonObject):
    join_as_guest(auth_client, alice_room["code"], "Lou")

    response: Response = auth_client.get(f"/rooms/{alice_room['code']}")

    assert response.status_code == 200
    assert response.json()["is_admin"] is False
    assert "guest_link" not in response.json()


def test_without_a_seat_the_room_is_not_found(auth_client: TestClient, alice_room: JsonObject):
    response: Response = auth_client.get(f"/rooms/{alice_room['code']}")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_the_cookie_of_a_room_does_not_open_another_one(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    other_room: JsonObject = create_room(
        auth_client, alice, create_template(auth_client, db_session, alice)
    )
    guest_link: str = join_as_guest(auth_client, alice_room["code"], "Lou").json()["guest_link"]
    # Le jeton de la première salle, envoyé sur les routes de l'autre
    auth_client.cookies.clear()
    auth_client.cookies.set(GUEST_COOKIE, token_of(guest_link), path=f"/rooms/{other_room['code']}")

    response: Response = auth_client.get(f"/rooms/{other_room['code']}")

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("nickname", "error_code"), [("   ", "string_too_short"), ("x" * 51, "string_too_long")]
)
def test_an_invalid_nickname_is_refused(
    auth_client: TestClient, alice_room: JsonObject, nickname: str, error_code: str
):
    response: Response = join_as_guest(auth_client, alice_room["code"], nickname)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "body.nickname"
    assert response.json()["errors"][0]["code"] == error_code


@pytest.mark.parametrize("nickname", ["LOU", "ALICE"])
def test_a_nickname_already_used_in_the_room_is_refused(
    auth_client: TestClient, alice_room: JsonObject, nickname: str
):
    # « Lou » est un invité, « alice » le nom affiché du room admin : la casse ne compte pas
    join_as_guest(auth_client, alice_room["code"], "Lou")
    auth_client.cookies.clear()

    response: Response = join_as_guest(auth_client, alice_room["code"], nickname)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.NICKNAME_TAKEN


def test_the_nickname_index_refusal_is_a_conflict_too(
    auth_client: TestClient, alice_room: JsonObject, monkeypatch: pytest.MonkeyPatch
):
    # Le service ne voit aucun nom pris (comme quand lower() diffère entre Python et PostgreSQL) :
    # c'est l'index unique de la base qui refuse le doublon
    join_as_guest(auth_client, alice_room["code"], "Lou")
    auth_client.cookies.clear()
    monkeypatch.setattr(RoomService, "_taken_names", staticmethod(lambda room: set()))

    response: Response = join_as_guest(auth_client, alice_room["code"], "lou")

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.NICKNAME_TAKEN


def test_joining_an_unknown_room_as_a_guest_is_not_found(auth_client: TestClient):
    response: Response = join_as_guest(auth_client, "ZZZZZZ", "Lou")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_the_link_validity_is_a_setting(
    auth_client: TestClient, alice_room: JsonObject, override_settings: Callable[..., None]
):
    override_settings(guest_link_ttl_days=7)

    response: Response = join_as_guest(auth_client, alice_room["code"], "Lou")

    expires_at: datetime = datetime.fromisoformat(response.json()["guest_link_expires_at"])
    assert abs(expires_at - (datetime.now(UTC) + timedelta(days=7))) < timedelta(minutes=1)
    assert "Max-Age=604" in response.headers["set-cookie"]


# --- Lien perso -----------------------------------------------------------------------------


def test_the_personal_link_gives_the_seat_back_on_another_device(
    auth_client: TestClient, alice_room: JsonObject
):
    code: str = alice_room["code"]
    joined: JsonObject = join_as_guest(auth_client, code, "Lou").json()
    # Autre appareil : aucun cookie
    auth_client.cookies.clear()

    response: Response = auth_client.post(
        f"/rooms/{code}/guest-session", json={"token": token_of(joined["guest_link"])}
    )

    assert response.status_code == 200
    assert response.json()["participants"] == joined["participants"]
    assert response.json()["guest_link"] == joined["guest_link"]
    assert response.json()["guest_link_expires_at"] == joined["guest_link_expires_at"]
    assert f"Path=/rooms/{code}" in response.headers["set-cookie"]
    assert auth_client.get(f"/rooms/{code}").status_code == 200


def test_an_unknown_personal_link_is_invalid(auth_client: TestClient, alice_room: JsonObject):
    response: Response = auth_client.post(
        f"/rooms/{alice_room['code']}/guest-session", json={"token": "unknown"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.GUEST_LINK_INVALID


def test_the_personal_link_dies_with_its_room(
    auth_client: TestClient, db_session: Session, alice_room: JsonObject
):
    guest_link: str = join_as_guest(auth_client, alice_room["code"], "Lou").json()["guest_link"]
    # Ce que fera la fermeture de la salle (#89)
    db_session.execute(delete(Room).where(Room.code == alice_room["code"]))

    response: Response = auth_client.post(
        f"/rooms/{alice_room['code']}/guest-session", json={"token": token_of(guest_link)}
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.GUEST_LINK_INVALID


def test_an_expired_seat_is_lost_and_frees_its_nickname(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    guest_link: str = join_as_guest(auth_client, code, "Lou").json()["guest_link"]
    guest_seat(db_session, "Lou").guest_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    by_cookie: Response = auth_client.get(f"/rooms/{code}")
    by_link: Response = auth_client.post(
        f"/rooms/{code}/guest-session", json={"token": token_of(guest_link)}
    )
    seen_by_alice: Response = auth_client.get(f"/rooms/{code}", headers=alice)
    auth_client.cookies.clear()
    new_lou: Response = join_as_guest(auth_client, code, "lou")

    assert by_cookie.status_code == 404
    assert by_link.json()["code"] == ErrorCode.GUEST_LINK_INVALID
    assert [p["display_name"] for p in seen_by_alice.json()["participants"]] == ["alice"]
    assert new_lou.status_code == 201
    assert len(db_session.scalars(select(Participant)).all()) == 2


# --- Compte et invité -----------------------------------------------------------------------


def test_an_account_is_served_before_a_guest_cookie(
    auth_client: TestClient, alice_room: JsonObject
):
    join_as_guest(auth_client, alice_room["code"], "Lou")
    bob: dict[str, str] = register(auth_client, "bob@example.com")

    # Bob n'a pas de place : son compte passe avant le cookie d'invité du même navigateur
    response: Response = auth_client.get(f"/rooms/{alice_room['code']}", headers=bob)

    assert response.status_code == 404


def test_a_guest_cannot_change_the_settings_nor_join_as_a_player(
    auth_client: TestClient, alice_room: JsonObject
):
    code: str = alice_room["code"]
    join_as_guest(auth_client, code, "Lou")

    settings_response: Response = auth_client.patch(
        f"/rooms/{code}/settings", json={"admin_plays": False}
    )
    join_response: Response = auth_client.post(f"/rooms/{code}/join")

    assert settings_response.status_code == 401
    assert join_response.status_code == 401
