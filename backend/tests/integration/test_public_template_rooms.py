from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from tests.integration.helpers import (
    JsonObject,
    ban_account,
    create_public_template,
    create_room,
    play_and_close,
    register,
    set_hidden,
    start_game,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"
BOB_EMAIL = "bob@example.com"


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, BOB_EMAIL)


@pytest.fixture
def public_template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_public_template(auth_client, db_session, alice, ALICE_EMAIL)


def make_private(client: TestClient, template_id: str, owner: dict[str, str]) -> None:
    response: Response = client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "private"}, headers=owner
    )
    assert response.status_code == 200


def delete_template(client: TestClient, template_id: str, owner: dict[str, str]) -> None:
    assert client.delete(f"/templates/{template_id}", headers=owner).status_code == 204


def test_a_user_starts_a_room_with_the_public_template_of_another_and_is_its_admin(
    auth_client: TestClient, bob: dict[str, str], public_template_id: str
):
    room: JsonObject = create_room(auth_client, bob, public_template_id)

    assert room["is_admin"] is True
    assert room["template"]["id"] == public_template_id
    assert room["template"]["name"] == "Food"


def test_the_template_stays_read_only_for_the_admin_of_the_room(
    auth_client: TestClient, bob: dict[str, str], public_template_id: str
):
    create_room(auth_client, bob, public_template_id)

    response: Response = auth_client.patch(
        f"/templates/{public_template_id}", json={"name": "Mine now"}, headers=bob
    )

    assert response.status_code == 404


Unavailable = Callable[[TestClient, Session, str, dict[str, str]], None]
UNAVAILABLE_CASES: dict[str, Unavailable] = {
    "private": lambda client, _, template_id, owner: make_private(client, template_id, owner),
    "hidden": lambda _, db_session, template_id, __: set_hidden(db_session, template_id),
    "deleted": lambda client, _, template_id, owner: delete_template(client, template_id, owner),
    "owner-banned": lambda _, db_session, __, ___: ban_account(db_session, ALICE_EMAIL),
}


@pytest.mark.parametrize("make_unavailable", UNAVAILABLE_CASES.values(), ids=UNAVAILABLE_CASES)
def test_a_room_cannot_start_with_a_template_of_another_that_is_no_longer_public(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    public_template_id: str,
    make_unavailable: Unavailable,
):
    make_unavailable(auth_client, db_session, public_template_id, alice)

    response: Response = auth_client.post(
        "/rooms", json={"template_id": public_template_id}, headers=bob
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_the_admin_plays_the_public_template_of_another_again_and_again(
    auth_client: TestClient, bob: dict[str, str], public_template_id: str
):
    code: str = create_room(auth_client, bob, public_template_id)["code"]

    start_game(auth_client, code, bob)
    play_and_close(auth_client, code, bob)
    room: JsonObject = start_game(auth_client, code, bob)

    assert room["status"] == "playing"


@pytest.mark.parametrize("make_unavailable", UNAVAILABLE_CASES.values(), ids=UNAVAILABLE_CASES)
def test_no_new_game_starts_once_the_template_of_another_is_no_longer_public(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    public_template_id: str,
    make_unavailable: Unavailable,
):
    code: str = create_room(auth_client, bob, public_template_id)["code"]
    make_unavailable(auth_client, db_session, public_template_id, alice)

    response: Response = auth_client.post(f"/rooms/{code}/game", headers=bob)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_a_game_in_progress_finishes_after_the_template_of_another_becomes_private(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], public_template_id: str
):
    code: str = create_room(auth_client, bob, public_template_id)["code"]
    start_game(auth_client, code, bob)
    make_private(auth_client, public_template_id, alice)

    room: JsonObject = play_and_close(auth_client, code, bob)

    assert room["status"] == "open"


def test_the_owner_still_plays_a_template_that_became_private(
    auth_client: TestClient, alice: dict[str, str], public_template_id: str
):
    code: str = create_room(auth_client, alice, public_template_id)["code"]
    make_private(auth_client, public_template_id, alice)

    room: JsonObject = start_game(auth_client, code, alice)

    assert room["status"] == "playing"
