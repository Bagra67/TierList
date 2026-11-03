import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.image import Image, ImageStatus
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.services.image_storage import quarantine_key
from tests.integration.conftest import FAKE_IMAGE_BASE_URL, FAKE_PRESIGNED_BASE_URL
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
    create_room,
    create_template,
    register,
    register_super_admin,
    start_game,
)

pytestmark = pytest.mark.integration

NOW: datetime = datetime.now(UTC)


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


def account(db_session: Session, email: str) -> User:
    return db_session.scalars(select(User).where(User.email == email)).one()


def add_image(
    db_session: Session,
    owner: User | None,
    hours_ago: float,
    status: ImageStatus = ImageStatus.VISIBLE,
) -> Image:
    image: Image = Image(
        owner_id=owner.id if owner is not None else None,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
        status=status,
        created_at=NOW - timedelta(hours=hours_ago),
    )
    db_session.add(image)
    db_session.flush()
    return image


def recent_uploads(client: TestClient, headers: dict[str, str], **params: str | int) -> Response:
    return client.get("/moderation/images", params=params, headers=headers)


def listed_ids(response: Response) -> list[str]:
    return [image["id"] for image in response.json()["images"]]


def test_the_images_are_listed_newest_first_with_their_author(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    older: Image = add_image(db_session, alice_account, hours_ago=5)
    newer: Image = add_image(db_session, alice_account, hours_ago=1)

    response: Response = recent_uploads(auth_client, nina)

    assert response.status_code == 200
    assert response.json()["has_more"] is False
    [first, second] = response.json()["images"]
    assert (first["id"], second["id"]) == (str(newer.id), str(older.id))
    assert first == {
        "id": str(newer.id),
        "url": f"{FAKE_IMAGE_BASE_URL}/{newer.storage_key}",
        "status": "visible",
        "created_at": first["created_at"],
        "author_id": str(alice_account.id),
        "author_name": "alice",
        "template_names": [],
        "game_count": 0,
    }


def test_the_pages_follow_each_other_without_gap_nor_duplicate(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    same_instant_images: list[Image] = [
        add_image(db_session, alice_account, hours_ago=2) for _ in range(3)
    ]
    images: list[Image] = [*same_instant_images, add_image(db_session, alice_account, hours_ago=1)]

    first: Response = recent_uploads(auth_client, nina, limit=2)
    second: Response = recent_uploads(auth_client, nina, limit=2, offset=2)

    assert first.json()["has_more"] is True
    assert second.json()["has_more"] is False
    listed: list[str] = listed_ids(first) + listed_ids(second)
    assert sorted(listed) == sorted(str(image.id) for image in images)
    assert listed[0] == str(images[-1].id)


def test_a_deleted_image_is_never_listed_and_a_hidden_one_is_shown_privately(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    hidden: Image = add_image(db_session, alice_account, hours_ago=1, status=ImageStatus.HIDDEN)
    add_image(db_session, alice_account, hours_ago=2, status=ImageStatus.DELETED)

    response: Response = recent_uploads(auth_client, nina)

    [listed] = response.json()["images"]
    assert (listed["id"], listed["status"]) == (str(hidden.id), "hidden")
    assert listed["url"] == f"{FAKE_PRESIGNED_BASE_URL}/{quarantine_key(hidden.storage_key)}"


@pytest.mark.parametrize(("status", "expected"), [("visible", "visible"), ("hidden", "hidden")])
def test_the_status_filter_keeps_only_that_status(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    status: str,
    expected: str,
):
    alice_account: User = account(db_session, "alice@example.com")
    add_image(db_session, alice_account, hours_ago=1)
    add_image(db_session, alice_account, hours_ago=2, status=ImageStatus.HIDDEN)

    response: Response = recent_uploads(auth_client, nina, status=status)

    assert [image["status"] for image in response.json()["images"]] == [expected]


@pytest.mark.parametrize("author", ["ALI", "alice@EXAMPLE", "lic"])
def test_the_author_filter_searches_the_name_and_the_email(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
    author: str,
):
    alice_image: Image = add_image(db_session, account(db_session, "alice@example.com"), 1)
    add_image(db_session, account(db_session, "bob@example.com"), 2)

    response: Response = recent_uploads(auth_client, nina, author=author)

    assert listed_ids(response) == [str(alice_image.id)]


def test_the_author_filter_reads_percent_as_a_plain_character(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    add_image(db_session, account(db_session, "alice@example.com"), 1)

    response: Response = recent_uploads(auth_client, nina, author="%")

    assert response.json()["images"] == []


def test_the_dates_keep_the_images_uploaded_in_the_period(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    add_image(db_session, alice_account, hours_ago=72)
    in_period: Image = add_image(db_session, alice_account, hours_ago=36)
    add_image(db_session, alice_account, hours_ago=1)

    response: Response = recent_uploads(
        auth_client,
        nina,
        created_after=(NOW - timedelta(hours=48)).isoformat(),
        created_before=(NOW - timedelta(hours=24)).isoformat(),
    )

    assert listed_ids(response) == [str(in_period.id)]


def test_a_date_without_time_zone_is_refused(auth_client: TestClient, nina: dict[str, str]):
    response: Response = recent_uploads(auth_client, nina, created_after="2026-10-01T00:00:00")

    assert response.status_code == 422


def test_an_image_whose_author_deleted_their_account_has_no_author_name(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    add_image(db_session, None, hours_ago=1)

    response: Response = recent_uploads(auth_client, nina)

    assert response.json()["images"][0]["author_name"] is None


def test_the_usage_counts_the_templates_and_the_games_of_an_image(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    image: Image = add_image(db_session, alice_account, hours_ago=1)
    played_id: str = create_template(auth_client, db_session, alice, tile_count=3)
    for tile in db_session.scalars(
        select(Tile).where(Tile.template_id == uuid.UUID(played_id), Tile.position < 2)
    ):
        tile.image_id = image.id
    other: Template = Template(owner_id=alice_account.id, name="Animals")
    other.tiles.append(Tile(text=None, image_id=image.id, position=0))
    deleted: Template = Template(owner_id=alice_account.id, name="Old", deleted_at=NOW)
    deleted.tiles.append(Tile(text=None, image_id=image.id, position=0))
    db_session.add_all([other, deleted])
    db_session.flush()
    room: JsonObject = create_room(auth_client, alice, played_id)
    start_game(auth_client, room["code"], alice)

    response: Response = recent_uploads(auth_client, nina)

    [listed] = response.json()["images"]
    assert listed["template_names"] == ["Animals", "Food"]
    assert listed["game_count"] == 1


def test_a_page_reads_the_usage_in_a_fixed_number_of_queries(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    add_image(db_session, alice_account, hours_ago=1)
    with counted_queries(db_session) as one_image:
        recent_uploads(auth_client, nina)
    for hours_ago in range(2, 12):
        add_image(db_session, alice_account, hours_ago=hours_ago)

    with counted_queries(db_session) as many_images:
        recent_uploads(auth_client, nina)

    assert len(many_images) == len(one_image)


def test_the_recent_uploads_require_a_session(auth_client: TestClient):
    response: Response = auth_client.get("/moderation/images")

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


def test_the_recent_uploads_refuse_other_accounts(auth_client: TestClient, alice: dict[str, str]):
    response: Response = recent_uploads(auth_client, alice)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.SUPER_ADMIN_REQUIRED


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 97}, {"status": "deleted"}])
def test_invalid_parameters_are_refused(
    auth_client: TestClient, nina: dict[str, str], params: dict[str, str | int]
):
    response: Response = recent_uploads(auth_client, nina, **params)

    assert response.status_code == 422
