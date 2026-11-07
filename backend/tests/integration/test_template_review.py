import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.tile import Tile
from app.models.user import User
from app.services.image_storage import quarantine_key
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
    create_template,
    register,
    register_super_admin,
)

pytestmark = pytest.mark.integration

QUERIES_MAX = 12


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice, tile_count=3)


def review(client: TestClient, headers: dict[str, str] | None, template_id: object) -> Response:
    return client.get(f"/moderation/templates/{template_id}", headers=headers)


def add_image_to_tile(db_session: Session, position: int, status: ImageStatus) -> Image:
    owner: User = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    image: Image = Image(
        owner_id=owner.id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="a" * 64,
        status=status,
    )
    db_session.add(image)
    tile: Tile = db_session.scalars(select(Tile).where(Tile.position == position)).one()
    tile.image = image
    db_session.flush()
    return image


def test_reading_a_template_refuses_visitors_and_other_accounts(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    assert review(auth_client, None, template_id).status_code == 401
    assert review(auth_client, bob, template_id).status_code == 403


def test_a_super_admin_reads_the_private_template_of_an_account(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    template_id: str,
):
    owner: User = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()

    response: Response = review(auth_client, nina, template_id)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert (body["id"], body["name"]) == (template_id, "Food")
    assert (body["owner_id"], body["owner_name"]) == (str(owner.id), "alice")
    assert (body["moderation"], body["moderation_reason"]) == ("none", None)
    assert [tier["position"] for tier in body["tiers"]] == list(range(len(body["tiers"])))
    assert body["tiers"]
    assert [tile["text"] for tile in body["tiles"]] == ["Tile 0", "Tile 1", "Tile 2"]
    assert body["tiles"][0]["image_url"] is None
    assert body["tiles"][0]["image_status"] is None


def test_a_hidden_image_stays_visible_and_a_deleted_image_has_no_address(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], template_id: str
):
    visible: Image = add_image_to_tile(db_session, 0, ImageStatus.VISIBLE)
    hidden: Image = add_image_to_tile(db_session, 1, ImageStatus.HIDDEN)
    add_image_to_tile(db_session, 2, ImageStatus.DELETED)

    tiles: list[JsonObject] = review(auth_client, nina, template_id).json()["tiles"]

    assert visible.storage_key in tiles[0]["image_url"]
    assert tiles[0]["image_status"] == "visible"
    assert quarantine_key(hidden.storage_key) in tiles[1]["image_url"]
    assert tiles[1]["image_status"] == "hidden"
    assert tiles[2]["image_url"] is None
    assert tiles[2]["image_status"] == "deleted"


def test_a_hidden_template_comes_with_its_reason(
    auth_client: TestClient, nina: dict[str, str], template_id: str
):
    hide: Response = auth_client.post(
        f"/moderation/templates/{template_id}/hide", json={"reason": "Illicite"}, headers=nina
    )
    assert hide.status_code == 204

    body: JsonObject = review(auth_client, nina, template_id).json()

    assert (body["moderation"], body["moderation_reason"]) == ("hidden", "Illicite")


def test_an_unknown_or_deleted_template_is_not_found(
    auth_client: TestClient, nina: dict[str, str], template_id: str
):
    delete: Response = auth_client.post(
        f"/moderation/templates/{template_id}/delete", json={"reason": "Illicite"}, headers=nina
    )
    assert delete.status_code == 204

    for unknown_id in (uuid.uuid4(), template_id):
        response: Response = review(auth_client, nina, unknown_id)

        assert response.status_code == 404
        assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_reading_a_template_writes_nothing_to_the_log(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], template_id: str
):
    assert review(auth_client, nina, template_id).status_code == 200

    assert db_session.scalars(select(ModerationAction)).first() is None


def test_the_number_of_queries_does_not_grow_with_the_tiles(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
):
    template_id: str = create_template(auth_client, db_session, alice, tile_count=12)
    for position in range(12):
        add_image_to_tile(db_session, position, ImageStatus.VISIBLE)

    with counted_queries(db_session) as statements:
        assert review(auth_client, nina, template_id).status_code == 200

    assert len(statements) <= QUERIES_MAX


def test_another_account_still_cannot_read_it_through_the_template_route(
    auth_client: TestClient, bob: dict[str, str], template_id: str
):
    response: Response = auth_client.get(f"/templates/{template_id}", headers=bob)

    assert response.status_code == 404
