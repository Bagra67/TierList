from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.marketplace import MARKETPLACE_PAGE_SIZE
from app.models.template_favorite import TemplateFavorite
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    ban_account,
    confirm_email,
    counted_queries,
    create_public_template,
    create_template,
    delete_template,
    make_private,
    register,
    set_hidden,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


@pytest.fixture
def bob(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    headers: dict[str, str] = register(auth_client, "bob@example.com")
    confirm_email(db_session, "bob@example.com")
    return headers


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_public_template(auth_client, db_session, alice, ALICE_EMAIL)


def favorite(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.put(f"/marketplace/templates/{template_id}/favorite", headers=headers)


def unfavorite(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.delete(f"/marketplace/templates/{template_id}/favorite", headers=headers)


def favorite_state(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.get(f"/marketplace/templates/{template_id}/favorite", headers=headers)


def favorites(
    client: TestClient, headers: dict[str, str], params: dict[str, str | int] | None = None
) -> Response:
    return client.get("/marketplace/favorites", params=params, headers=headers)


def favorite_ids(client: TestClient, headers: dict[str, str]) -> list[str]:
    page: JsonObject = favorites(client, headers).json()
    return [card["id"] for card in page["items"]]


def stored_favorite_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(TemplateFavorite)) or 0


def test_a_user_adds_the_public_template_of_another_to_their_favorites(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    response: Response = favorite(auth_client, template_id, bob)

    assert response.status_code == 200
    assert response.json() == {"favorited": True, "can_favorite": True}
    assert favorite_state(auth_client, template_id, bob).json() == {
        "favorited": True,
        "can_favorite": True,
    }
    assert favorite_ids(auth_client, bob) == [template_id]


def test_adding_a_favorite_again_keeps_a_single_favorite(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], template_id: str
):
    favorite(auth_client, template_id, bob)

    response: Response = favorite(auth_client, template_id, bob)

    assert response.json() == {"favorited": True, "can_favorite": True}
    assert stored_favorite_count(db_session) == 1


def test_a_user_removes_a_template_from_their_favorites(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    favorite(auth_client, template_id, bob)

    response: Response = unfavorite(auth_client, template_id, bob)

    assert response.json() == {"favorited": False, "can_favorite": True}
    assert unfavorite(auth_client, template_id, bob).json() == {
        "favorited": False,
        "can_favorite": True,
    }
    assert favorite_ids(auth_client, bob) == []


def test_a_user_cannot_add_their_own_template_to_their_favorites(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    response: Response = favorite(auth_client, template_id, alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_FAVORITE_OWN_TEMPLATE
    assert stored_favorite_count(db_session) == 0


def test_the_owner_reads_that_they_cannot_add_their_template_to_their_favorites(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    response: Response = favorite_state(auth_client, template_id, alice)

    assert response.json() == {"favorited": False, "can_favorite": False}


def test_adding_a_favorite_requires_a_confirmed_email(
    auth_client: TestClient, db_session: Session, template_id: str
):
    unconfirmed: dict[str, str] = register(auth_client, "dave@example.com")

    response: Response = favorite(auth_client, template_id, unconfirmed)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.EMAIL_NOT_VERIFIED
    assert stored_favorite_count(db_session) == 0


def test_the_favorites_require_an_account(auth_client: TestClient, template_id: str):
    assert auth_client.put(f"/marketplace/templates/{template_id}/favorite").status_code == 401
    assert auth_client.get("/marketplace/favorites").status_code == 401


def test_the_private_template_of_another_cannot_be_added_to_the_favorites(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
):
    private_template_id: str = create_template(auth_client, db_session, alice)

    response: Response = favorite(auth_client, private_template_id, bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


@pytest.fixture(params=["private", "hidden", "deleted", "owner-banned"])
def make_unavailable(
    request: pytest.FixtureRequest,
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    template_id: str,
) -> Callable[[], None]:
    def make_it_unavailable() -> None:
        match request.param:
            case "private":
                make_private(auth_client, template_id, alice)
            case "hidden":
                set_hidden(db_session, template_id)
            case "deleted":
                delete_template(auth_client, template_id, alice)
            case _:
                ban_account(db_session, ALICE_EMAIL)

    return make_it_unavailable


def test_a_favorite_that_is_no_longer_listed_is_kept_but_not_shown(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    template_id: str,
    make_unavailable: Callable[[], None],
):
    favorite(auth_client, template_id, bob)
    make_unavailable()

    assert favorite_ids(auth_client, bob) == []
    assert favorite_state(auth_client, template_id, bob).status_code == 404
    assert favorite(auth_client, template_id, bob).status_code == 404
    assert unfavorite(auth_client, template_id, bob).status_code == 404
    assert stored_favorite_count(db_session) == 1


def test_a_favorite_comes_back_when_the_template_is_public_again(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], template_id: str
):
    favorite(auth_client, template_id, bob)
    make_private(auth_client, template_id, alice)

    response: Response = auth_client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}, headers=alice
    )

    assert response.status_code == 200
    assert favorite_ids(auth_client, bob) == [template_id]


def test_deleting_an_account_removes_its_favorites(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], template_id: str
):
    favorite(auth_client, template_id, bob)

    response: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=bob
    )

    assert response.status_code == 204
    assert stored_favorite_count(db_session) == 0


def test_the_favorites_are_marketplace_cards_most_recently_added_first(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    favorite(auth_client, other_template_id, bob)
    favorite(auth_client, template_id, bob)

    page: JsonObject = favorites(auth_client, bob).json()

    assert [card["id"] for card in page["items"]] == [template_id, other_template_id]
    assert page["next_cursor"] is None
    assert {"name", "owner_name", "tags", "tile_count", "like_count"} <= page["items"][0].keys()


def test_the_favorites_are_read_page_by_page(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    favorite(auth_client, other_template_id, bob)
    favorite(auth_client, template_id, bob)

    first: JsonObject = favorites(auth_client, bob, {"limit": 1}).json()
    second: JsonObject = favorites(
        auth_client, bob, {"limit": 1, "cursor": first["next_cursor"]}
    ).json()

    assert [card["id"] for card in first["items"]] == [template_id]
    assert [card["id"] for card in second["items"]] == [other_template_id]
    assert second["next_cursor"] is None


def test_the_favorites_of_another_account_are_not_shown(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], template_id: str
):
    favorite(auth_client, template_id, bob)
    carol: dict[str, str] = register(auth_client, "carol@example.com")

    assert favorite_ids(auth_client, carol) == []


def test_an_unreadable_favorites_cursor_is_refused(auth_client: TestClient, bob: dict[str, str]):
    response: Response = favorites(auth_client, bob, {"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.INVALID_CURSOR


def test_a_page_of_favorites_needs_the_same_queries_whatever_its_size(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    favorite(auth_client, template_id, bob)
    with counted_queries(db_session) as one_favorite:
        favorites(auth_client, bob)
    for _ in range(4):
        favorite(
            auth_client,
            create_public_template(auth_client, db_session, alice, ALICE_EMAIL),
            bob,
        )
    with counted_queries(db_session) as five_favorites:
        favorites(auth_client, bob)

    assert len(five_favorites) == len(one_favorite)


def favorite_states(
    client: TestClient, template_ids: list[str], headers: dict[str, str]
) -> Response:
    return client.get(
        "/marketplace/favorite-states", params={"template_id": template_ids}, headers=headers
    )


def test_a_user_reads_the_favorite_states_of_a_page_of_cards(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    private_template_id: str = create_template(auth_client, db_session, alice)
    favorite(auth_client, template_id, bob)

    response: Response = favorite_states(
        auth_client, [other_template_id, private_template_id, template_id], bob
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"template_id": other_template_id, "favorited": False, "can_favorite": True},
            {"template_id": template_id, "favorited": True, "can_favorite": True},
        ]
    }


def test_the_owner_reads_on_the_cards_that_they_cannot_add_their_template_to_their_favorites(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    response: Response = favorite_states(auth_client, [template_id, template_id], alice)

    assert response.json() == {
        "items": [{"template_id": template_id, "favorited": False, "can_favorite": False}]
    }


def test_reading_the_favorite_states_requires_an_account(auth_client: TestClient, template_id: str):
    response: Response = auth_client.get(
        "/marketplace/favorite-states", params={"template_id": [template_id]}
    )

    assert response.status_code == 401


@pytest.mark.parametrize("id_count", [0, MARKETPLACE_PAGE_SIZE + 1])
def test_the_favorite_states_take_between_one_id_and_one_page_of_ids(
    auth_client: TestClient, bob: dict[str, str], template_id: str, id_count: int
):
    response: Response = favorite_states(auth_client, [template_id] * id_count, bob)

    assert response.status_code == 422
