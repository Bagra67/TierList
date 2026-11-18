from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.template_like import TemplateLike
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    ban_account,
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
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def carol(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "carol@example.com")


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
    assert response.json() == {"liked": True, "like_count": 1}
    assert public_like_count(auth_client, template_id) == 1


def test_liking_again_keeps_a_single_like(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)

    response: Response = like(auth_client, template_id, bob)

    assert response.json() == {"liked": True, "like_count": 1}


def test_every_account_counts_once(
    auth_client: TestClient, bob: dict[str, str], carol: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)
    like(auth_client, template_id, carol)

    assert like_state(auth_client, template_id, bob).json() == {"liked": True, "like_count": 2}


def test_a_user_removes_their_like(
    auth_client: TestClient, bob: dict[str, str], carol: dict[str, str], template_id: str
):
    like(auth_client, template_id, bob)
    like(auth_client, template_id, carol)

    response: Response = unlike(auth_client, template_id, bob)

    assert response.json() == {"liked": False, "like_count": 1}
    assert unlike(auth_client, template_id, bob).json() == {"liked": False, "like_count": 1}


def test_a_user_cannot_like_their_own_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    response: Response = like(auth_client, template_id, alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_LIKE_OWN_TEMPLATE
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
