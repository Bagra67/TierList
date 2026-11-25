import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.templates import FREE_PLAN_MAX_TILES
from app.models.template import Template
from app.models.tile import Tile
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    add_tile_with_image,
    ban_account,
    confirm_email,
    counted_queries,
    create_public_template,
    delete_template,
    make_private,
    register,
    register_super_admin,
    set_hidden,
    stored_template,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"
BOB_EMAIL = "bob@example.com"
CAROL_EMAIL = "carol@example.com"


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, BOB_EMAIL)


@pytest.fixture
def carol(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, CAROL_EMAIL)


def allow_copies(
    client: TestClient, template_id: str, owner: dict[str, str], allowed: bool = True
) -> Response:
    return client.put(
        f"/templates/{template_id}/forks-allowed", json={"forks_allowed": allowed}, headers=owner
    )


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    created_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    assert allow_copies(auth_client, created_id, alice).status_code == 200
    return created_id


def copy(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.post(f"/marketplace/templates/{template_id}/copy", headers=headers)


def copied_id(client: TestClient, template_id: str, headers: dict[str, str]) -> str:
    response: Response = copy(client, template_id, headers)
    assert response.status_code == 201
    return response.json()["id"]


def can_copy(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.get(f"/marketplace/templates/{template_id}/copy", headers=headers)


def publish_with_copies(
    client: TestClient, db_session: Session, template_id: str, owner: dict[str, str], email: str
) -> None:
    confirm_email(db_session, email)
    response: Response = client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}, headers=owner
    )
    assert response.status_code == 200
    assert allow_copies(client, template_id, owner).status_code == 200


def lineage(client: TestClient, template_id: str) -> list[JsonObject]:
    page: JsonObject = client.get(f"/marketplace/templates/{template_id}").json()
    return page["lineage"]


def copy_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Template)) or 0


def test_copies_are_not_allowed_by_default(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
):
    source_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)

    response: Response = copy(auth_client, source_id, bob)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.COPY_NOT_ALLOWED
    assert auth_client.get(f"/marketplace/templates/{source_id}").json()["copy_allowed"] is False


def test_a_user_copies_a_public_template_into_a_private_template_of_their_own(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    _, image = add_tile_with_image(auth_client, db_session, alice, template_id, "Photo")
    tags: Response = auth_client.put(
        f"/templates/{template_id}/tags", json={"tags": ["Apéro"]}, headers=alice
    )
    assert tags.status_code == 200

    response: Response = copy(auth_client, template_id, bob)

    assert response.status_code == 201
    body: JsonObject = response.json()
    assert body["visibility"] == "private"
    assert body["forks_allowed"] is False
    assert body["first_made_public_at"] is None
    assert body["copied_from"] == "Food"
    assert body["tags"] == ["Apéro"]
    assert [tier["name"] for tier in body["tiers"]] == ["S", "A", "B", "C", "D", "E"]
    assert [tile["text"] for tile in body["tiles"]] == ["Tile 0", "Tile 1", "Tile 2", "Photo"]
    copy_template: Template = stored_template(db_session, body["id"])
    assert copy_template.owner_id != stored_template(db_session, template_id).owner_id
    assert copy_template.tiles[3].image_id == image.id
    assert copy_template.search_text == "food apero"
    assert auth_client.get(f"/templates/{body['id']}", headers=bob).status_code == 200


def test_a_user_cannot_copy_their_own_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    before: int = copy_count(db_session)

    response: Response = copy(auth_client, template_id, alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_COPY_OWN_TEMPLATE
    assert copy_count(db_session) == before
    assert can_copy(auth_client, template_id, alice).json() == {"can_copy": False}


def test_copying_requires_an_account(auth_client: TestClient, template_id: str):
    assert auth_client.post(f"/marketplace/templates/{template_id}/copy").status_code == 401


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


def test_a_template_that_is_not_listed_cannot_be_copied(
    auth_client: TestClient,
    bob: dict[str, str],
    template_id: str,
    make_unavailable: Callable[[], None],
):
    make_unavailable()

    response: Response = copy(auth_client, template_id, bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND
    assert can_copy(auth_client, template_id, bob).status_code == 404


def test_stopping_the_copies_keeps_the_copies_already_made(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    existing_copy_id: str = copied_id(auth_client, template_id, bob)
    assert can_copy(auth_client, template_id, bob).json() == {"can_copy": True}

    response: Response = allow_copies(auth_client, template_id, alice, allowed=False)

    assert response.json()["forks_allowed"] is False
    assert copy(auth_client, template_id, bob).json()["code"] == ErrorCode.COPY_NOT_ALLOWED
    assert can_copy(auth_client, template_id, bob).json() == {"can_copy": False}
    assert auth_client.get(f"/templates/{existing_copy_id}", headers=bob).status_code == 200


def test_only_the_owner_allows_the_copies(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    assert allow_copies(auth_client, template_id, bob).status_code == 404


def test_the_lineage_credits_every_ancestor_up_to_the_original(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    carol: dict[str, str],
    template_id: str,
):
    bob_copy_id: str = copied_id(auth_client, template_id, bob)
    publish_with_copies(auth_client, db_session, bob_copy_id, bob, BOB_EMAIL)
    carol_copy_id: str = copied_id(auth_client, bob_copy_id, carol)
    publish_with_copies(auth_client, db_session, carol_copy_id, carol, CAROL_EMAIL)

    assert lineage(auth_client, carol_copy_id) == [
        {"template_id": bob_copy_id, "name": "Food", "owner_name": "bob"},
        {"template_id": template_id, "name": "Food", "owner_name": "alice"},
    ]
    assert lineage(auth_client, template_id) == []


def test_an_ancestor_that_is_no_longer_listed_keeps_its_name_without_a_link(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    bob_copy_id: str = copied_id(auth_client, template_id, bob)
    publish_with_copies(auth_client, db_session, bob_copy_id, bob, BOB_EMAIL)
    rename_response: Response = auth_client.patch(
        f"/templates/{template_id}", json={"name": "Secret name"}, headers=alice
    )
    assert rename_response.status_code == 200
    make_private(auth_client, template_id, alice)

    assert lineage(auth_client, bob_copy_id) == [
        {"template_id": None, "name": "Food", "owner_name": "alice"}
    ]


def test_a_listed_ancestor_shows_its_current_name(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
):
    bob_copy_id: str = copied_id(auth_client, template_id, bob)
    publish_with_copies(auth_client, db_session, bob_copy_id, bob, BOB_EMAIL)
    auth_client.patch(f"/templates/{template_id}", json={"name": "Snacks"}, headers=alice)

    assert lineage(auth_client, bob_copy_id)[0]["name"] == "Snacks"


def test_the_lineage_outlives_the_purge_and_the_deletion_of_the_owner_account(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    carol: dict[str, str],
    template_id: str,
):
    bob_copy_id: str = copied_id(auth_client, template_id, bob)
    publish_with_copies(auth_client, db_session, bob_copy_id, bob, BOB_EMAIL)
    carol_copy_id: str = copied_id(auth_client, bob_copy_id, carol)
    publish_with_copies(auth_client, db_session, carol_copy_id, carol, CAROL_EMAIL)

    db_session.execute(delete(Template).where(Template.id == uuid.UUID(bob_copy_id)))
    db_session.flush()
    response: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=alice
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert lineage(auth_client, carol_copy_id) == [
        {"template_id": None, "name": "Food", "owner_name": None},
        {"template_id": None, "name": "Food", "owner_name": None},
    ]


def test_the_cards_name_the_template_a_copy_comes_from(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    template_id: str,
):
    bob_copy_id: str = copied_id(auth_client, template_id, bob)
    publish_with_copies(auth_client, db_session, bob_copy_id, bob, BOB_EMAIL)

    cards: list[JsonObject] = auth_client.get(
        "/marketplace/templates", params={"sort": "newest"}
    ).json()["items"]

    copied_from: dict[str, JsonObject | None] = {card["id"]: card["copied_from"] for card in cards}
    assert copied_from == {
        bob_copy_id: {"template_id": template_id, "name": "Food", "owner_name": "alice"},
        template_id: None,
    }


def test_a_page_of_cards_needs_the_same_queries_with_copies(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    template_id: str,
):
    with counted_queries(db_session) as without_copies:
        auth_client.get("/marketplace/templates")
    for _ in range(3):
        publish_with_copies(
            auth_client, db_session, copied_id(auth_client, template_id, bob), bob, BOB_EMAIL
        )
    with counted_queries(db_session) as with_copies:
        auth_client.get("/marketplace/templates")

    assert len(with_copies) == len(without_copies)


def published_official(client: TestClient, db_session: Session, tile_count: int) -> str:
    nina: dict[str, str] = register_super_admin(client, db_session, "nina@example.com")
    official_id: str = client.post(
        "/moderation/official-templates", json={"name": "Cheeses"}, headers=nina
    ).json()["id"]
    for position in range(tile_count):
        db_session.add(
            Tile(template_id=uuid.UUID(official_id), text=f"Tile {position}", position=position)
        )
    db_session.flush()
    client.post(f"/moderation/official-templates/{official_id}/lock", headers=nina)
    assert allow_copies(client, official_id, nina).status_code == 200
    publish: Response = client.post(
        f"/moderation/official-templates/{official_id}/publish", headers=nina
    )
    assert publish.status_code == 200
    return official_id


def test_a_template_larger_than_a_copy_can_keep_cannot_be_copied(
    auth_client: TestClient, db_session: Session, bob: dict[str, str]
):
    official_id: str = published_official(auth_client, db_session, FREE_PLAN_MAX_TILES + 1)

    response: Response = copy(auth_client, official_id, bob)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_TOO_LARGE_TO_COPY
    assert response.json()["params"] == {"max_tiles": FREE_PLAN_MAX_TILES, "max_tags": 5}
    assert auth_client.get(f"/marketplace/templates/{official_id}").json()["copy_allowed"] is False


def test_an_official_template_within_the_limits_becomes_a_template_of_the_player(
    auth_client: TestClient, db_session: Session, bob: dict[str, str]
):
    official_id: str = published_official(auth_client, db_session, 3)

    response: Response = copy(auth_client, official_id, bob)

    assert response.status_code == 201
    assert response.json()["official"] is False
    assert response.json()["max_tiles"] == FREE_PLAN_MAX_TILES
