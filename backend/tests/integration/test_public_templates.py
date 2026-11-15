from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.templates import DEFAULT_TIERS
from app.models.account_ban import AccountBan
from app.models.image import ImageStatus
from app.models.user import User
from tests.integration.conftest import FAKE_IMAGE_BASE_URL
from tests.integration.helpers import (
    JsonObject,
    add_tile_with_image,
    create_public_template,
    create_template,
    register,
    set_hidden,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_public_template(auth_client, db_session, alice, ALICE_EMAIL)


def public_template(client: TestClient, template_id: str) -> Response:
    return client.get(f"/marketplace/templates/{template_id}")


def alice_user(db_session: Session) -> User:
    return db_session.scalars(select(User).where(User.email == ALICE_EMAIL)).one()


def days_ago(days: int | None) -> datetime | None:
    return None if days is None else datetime.now(UTC) - timedelta(days=days)


def ban_alice(db_session: Session, ends_at: datetime | None, lifted_at: datetime | None) -> None:
    db_session.add(
        AccountBan(
            user_id=alice_user(db_session).id,
            actor_name="Nina",
            reason="Spam",
            ends_at=ends_at,
            lifted_at=lifted_at,
        )
    )
    db_session.flush()


def test_a_visitor_sees_a_public_template_with_its_owner_tags_tiers_and_tiles(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    auth_client.put(
        f"/templates/{template_id}/tags", json={"tags": ["Snacks", "Party"]}, headers=alice
    )

    response: Response = public_template(auth_client, template_id)

    assert response.status_code == 200
    template: JsonObject = response.json()
    assert template["id"] == template_id
    assert template["name"] == "Food"
    assert template["owner_name"] == "alice"
    assert template["tags"] == ["Snacks", "Party"]
    assert [tier["name"] for tier in template["tiers"]] == [name for name, _ in DEFAULT_TIERS]
    assert [tile["text"] for tile in template["tiles"]] == ["Tile 0", "Tile 1", "Tile 2"]


def test_a_public_template_shows_nothing_reserved_to_its_owner(
    auth_client: TestClient, template_id: str
):
    template: JsonObject = public_template(auth_client, template_id).json()

    assert set(template) == {"id", "name", "owner_name", "tags", "tiers", "tiles"}
    assert set(template["tiles"][0]) == {"id", "text", "image_url", "image_removed"}


def test_a_visible_image_has_its_url_and_a_removed_one_has_none(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    _, visible = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    _, hidden = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    hidden.status = ImageStatus.HIDDEN
    db_session.flush()

    tiles: list[JsonObject] = public_template(auth_client, template_id).json()["tiles"]

    assert tiles[-2]["image_url"] == f"{FAKE_IMAGE_BASE_URL}/{visible.storage_key}"
    assert tiles[-2]["image_removed"] is False
    assert tiles[-1]["image_url"] is None
    assert tiles[-1]["image_removed"] is True


def test_a_private_template_is_not_available(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    private_template_id: str = create_template(auth_client, db_session, alice)

    response: Response = public_template(auth_client, private_template_id)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_a_template_made_private_again_is_not_available(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    auth_client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "private"}, headers=alice
    )

    assert public_template(auth_client, template_id).status_code == 404


def test_a_hidden_public_template_is_not_available(
    auth_client: TestClient, db_session: Session, template_id: str
):
    set_hidden(db_session, template_id)

    assert public_template(auth_client, template_id).status_code == 404


def test_a_deleted_public_template_is_not_available(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    auth_client.delete(f"/templates/{template_id}", headers=alice)

    assert public_template(auth_client, template_id).status_code == 404


def test_an_unknown_template_is_not_available(auth_client: TestClient):
    response: Response = public_template(auth_client, "00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


@pytest.mark.parametrize("ends_in_days", [None, 3], ids=["permanent", "temporary"])
def test_the_template_of_a_banned_owner_is_not_available(
    auth_client: TestClient, db_session: Session, template_id: str, ends_in_days: int | None
):
    ends_at: datetime | None = (
        datetime.now(UTC) + timedelta(days=ends_in_days) if ends_in_days is not None else None
    )
    ban_alice(db_session, ends_at, lifted_at=None)

    assert public_template(auth_client, template_id).status_code == 404


@pytest.mark.parametrize(
    ("ends_days_ago", "lifted_days_ago"), [(1, None), (None, 1)], ids=["ended", "lifted"]
)
def test_the_template_is_available_again_once_the_ban_ends_or_is_lifted(
    auth_client: TestClient,
    db_session: Session,
    template_id: str,
    ends_days_ago: int | None,
    lifted_days_ago: int | None,
):
    ban_alice(db_session, days_ago(ends_days_ago), days_ago(lifted_days_ago))

    assert public_template(auth_client, template_id).status_code == 200


def test_an_invalid_account_token_does_not_prevent_reading_a_public_template(
    auth_client: TestClient, template_id: str
):
    response: Response = auth_client.get(
        f"/marketplace/templates/{template_id}", headers={"Authorization": "Bearer invalid"}
    )

    assert response.status_code == 200
