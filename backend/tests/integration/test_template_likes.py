from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.marketplace import MARKETPLACE_PAGE_SIZE
from app.models.template_like import TemplateLike
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    ban_account,
    confirm_email,
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


def confirmed_account(client: TestClient, db_session: Session, email: str) -> dict[str, str]:
    headers: dict[str, str] = register(client, email)
    confirm_email(db_session, email)
    return headers


@pytest.fixture
def bob(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return confirmed_account(auth_client, db_session, "bob@example.com")


@pytest.fixture
def carol(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return confirmed_account(auth_client, db_session, "carol@example.com")


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_public_template(auth_client, db_session, alice, ALICE_EMAIL)


def like(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.put(f"/marketplace/templates/{template_id}/like", headers=headers)


def unlike(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.delete(f"/marketplace/templates/{template_id}/like", headers=headers)


def like_state(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.get(f"/marketplace/templates/{template_id}/like", headers=headers)


def public_like_count(client: TestClient, template_id: str) -> int:
    page: JsonObject = client.get(f"/marketplace/templates/{template_id}").json()
    return page["like_count"]


def stored_like_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(TemplateLike)) or 0


def test_a_user_likes_the_public_template_of_another(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    response: Response = like(auth_client, template_id, bob)

    assert response.status_code == 200
    assert response.json() == {"liked": True, "like_count": 1, "can_like": True}
    assert public_like_count(auth_client, template_id) == 1


def test_liking_again_keeps_a_single_like(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)

    response: Response = like(auth_client, template_id, bob)

    assert response.json() == {"liked": True, "like_count": 1, "can_like": True}


def test_every_account_counts_once(
    auth_client: TestClient, bob: dict[str, str], carol: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)
    like(auth_client, template_id, carol)

    assert like_state(auth_client, template_id, bob).json() == {
        "liked": True,
        "like_count": 2,
        "can_like": True,
    }


def test_a_user_removes_their_like(
    auth_client: TestClient, bob: dict[str, str], carol: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)
    like(auth_client, template_id, carol)

    response: Response = unlike(auth_client, template_id, bob)

    assert response.json() == {"liked": False, "like_count": 1, "can_like": True}
    assert unlike(auth_client, template_id, bob).json() == {
        "liked": False,
        "like_count": 1,
        "can_like": True,
    }


def test_a_user_cannot_like_their_own_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    response: Response = like(auth_client, template_id, alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_LIKE_OWN_TEMPLATE
    assert stored_like_count(db_session) == 0


def test_the_owner_reads_that_they_cannot_like_their_template(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    response: Response = like_state(auth_client, template_id, alice)

    assert response.json() == {"liked": False, "like_count": 0, "can_like": False}


def test_liking_requires_a_confirmed_email(
    auth_client: TestClient, db_session: Session, template_id: str
):
    unconfirmed: dict[str, str] = register(auth_client, "dave@example.com")

    response: Response = like(auth_client, template_id, unconfirmed)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.EMAIL_NOT_VERIFIED
    assert stored_like_count(db_session) == 0


def test_liking_requires_an_account(auth_client: TestClient, template_id: str):
    assert auth_client.put(f"/marketplace/templates/{template_id}/like").status_code == 401


def test_the_private_template_of_another_cannot_be_liked(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
):
    private_template_id: str = create_template(auth_client, db_session, alice)

    response: Response = like(auth_client, private_template_id, bob)

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


def test_the_likes_of_a_template_that_is_no_longer_listed_are_kept_but_not_shown(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    template_id: str,
    make_unavailable: Callable[[], None],
):
    like(auth_client, template_id, bob)
    make_unavailable()

    assert like_state(auth_client, template_id, bob).status_code == 404
    assert like(auth_client, template_id, bob).status_code == 404
    assert unlike(auth_client, template_id, bob).status_code == 404
    assert stored_like_count(db_session) == 1


def test_the_likes_come_back_when_the_template_is_public_again(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)
    make_private(auth_client, template_id, alice)

    response: Response = auth_client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}, headers=alice
    )

    assert response.status_code == 200
    assert public_like_count(auth_client, template_id) == 1


def test_deleting_an_account_removes_its_likes(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)

    response: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=bob
    )

    assert response.status_code == 204
    assert public_like_count(auth_client, template_id) == 0


def like_states(client: TestClient, template_ids: list[str], headers: dict[str, str]) -> Response:
    return client.get("/marketplace/likes", params={"template_id": template_ids}, headers=headers)


def test_a_user_reads_the_like_states_of_a_page_of_cards(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    like(auth_client, template_id, bob)

    response: Response = like_states(auth_client, [other_template_id, template_id], bob)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"template_id": other_template_id, "liked": False, "like_count": 0, "can_like": True},
            {"template_id": template_id, "liked": True, "like_count": 1, "can_like": True},
        ]
    }


def test_the_owner_reads_on_the_cards_that_they_cannot_like_their_template(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)

    response: Response = like_states(auth_client, [template_id, template_id], alice)

    assert response.json() == {
        "items": [{"template_id": template_id, "liked": False, "like_count": 1, "can_like": False}]
    }


def test_the_like_states_leave_out_the_templates_that_are_not_listed(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    private_template_id: str = create_template(auth_client, db_session, alice)

    response: Response = like_states(auth_client, [private_template_id, template_id], bob)

    assert [item["template_id"] for item in response.json()["items"]] == [template_id]


def test_reading_the_like_states_requires_an_account(auth_client: TestClient, template_id: str):
    response: Response = auth_client.get(
        "/marketplace/likes", params={"template_id": [template_id]}
    )

    assert response.status_code == 401


@pytest.mark.parametrize("id_count", [0, MARKETPLACE_PAGE_SIZE + 1])
def test_the_like_states_take_between_one_id_and_one_page_of_ids(
    auth_client: TestClient, bob: dict[str, str], template_id: str, id_count: int
):
    response: Response = like_states(auth_client, [template_id] * id_count, bob)

    assert response.status_code == 422
