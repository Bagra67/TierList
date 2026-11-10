import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.user import User
from app.repositories import images as image_repository
from app.services import account_review as account_review_module
from app.services.image_storage import quarantine_key
from tests.integration.helpers import (
    JsonObject,
    create_template,
    register,
    register_super_admin,
)

pytestmark = pytest.mark.integration

FILE_CONTENT: bytes = b"webp"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


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
    stored_images: dict[str, bytes],
    owner: User,
    status: ImageStatus = ImageStatus.VISIBLE,
) -> Image:
    image: Image = Image(
        owner_id=owner.id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=len(FILE_CONTENT),
        sha256="0" * 64,
        status=status,
    )
    db_session.add(image)
    db_session.flush()
    if status == ImageStatus.VISIBLE:
        stored_images[image.storage_key] = FILE_CONTENT
    elif status == ImageStatus.HIDDEN:
        stored_images[quarantine_key(image.storage_key)] = FILE_CONTENT
    return image


def log_entry(db_session: Session, actor: User, target_id: uuid.UUID | None, label: str) -> None:
    db_session.add(
        ModerationAction(
            actor_id=actor.id,
            actor_name=actor.display_name,
            action=ModerationActionKind.HIDE,
            target_type=ModerationTargetType.TEMPLATE,
            target_id=target_id,
            target_label=label,
            reason="Harassment",
            created_at=datetime.now(UTC) - timedelta(minutes=len(label)),
        )
    )
    db_session.flush()


def search(client: TestClient, headers: dict[str, str], **params: str | int) -> Response:
    return client.get("/moderation/accounts", params=params, headers=headers)


def names(response: Response) -> list[str]:
    return [listed["display_name"] for listed in response.json()["accounts"]]


@pytest.mark.parametrize("query", ["ALI", "alice@EXAMPLE", "lic"])
def test_the_search_finds_an_account_by_name_or_email(
    auth_client: TestClient,
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
    query: str,
):
    response: Response = search(auth_client, nina, query=query)

    assert response.status_code == 200
    assert names(response) == ["alice"]
    [found] = response.json()["accounts"]
    assert set(found) == {"id", "display_name", "email", "created_at", "role", "banned"}
    assert (found["email"], found["role"], found["banned"]) == ("alice@example.com", "user", False)


def test_the_search_without_text_lists_every_account_by_name_page_by_page(
    auth_client: TestClient, nina: dict[str, str], alice: dict[str, str], bob: dict[str, str]
):
    first: Response = search(auth_client, nina, limit=2)
    second: Response = search(auth_client, nina, limit=2, offset=2)

    assert (names(first), first.json()["has_more"]) == (["alice", "bob"], True)
    assert (names(second), second.json()["has_more"]) == (["nina"], False)


def test_the_search_reads_percent_as_a_plain_character(
    auth_client: TestClient, nina: dict[str, str], alice: dict[str, str]
):
    response: Response = search(auth_client, nina, query="%")

    assert response.json()["accounts"] == []


def test_the_account_page_shows_its_details_and_its_templates(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
):
    alice_account: User = account(db_session, "alice@example.com")
    template_id: str = create_template(auth_client, db_session, alice)
    deleted: Template = Template(
        owner_id=alice_account.id, name="Old", deleted_at=datetime.now(UTC)
    )
    db_session.add(deleted)
    db_session.flush()

    response: Response = auth_client.get(f"/moderation/accounts/{alice_account.id}", headers=nina)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert (body["display_name"], body["email"], body["email_verified"], body["role"]) == (
        "alice",
        "alice@example.com",
        False,
        "user",
    )
    [template] = body["templates"]
    assert (template["id"], template["name"], template["tile_count"], template["moderation"]) == (
        template_id,
        "Food",
        3,
        "none",
    )


def test_an_unknown_account_is_not_found(auth_client: TestClient, nina: dict[str, str]):
    response: Response = auth_client.get(f"/moderation/accounts/{uuid.uuid4()}", headers=nina)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ACCOUNT_NOT_FOUND


def test_hiding_all_the_images_hides_each_visible_one_with_its_log_entry(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
):
    alice_account: User = account(db_session, "alice@example.com")
    visible: list[Image] = [add_image(db_session, stored_images, alice_account) for _ in range(2)]
    add_image(db_session, stored_images, alice_account, ImageStatus.HIDDEN)
    add_image(db_session, stored_images, alice_account, ImageStatus.DELETED)
    bob_image: Image = add_image(db_session, stored_images, account(db_session, "bob@example.com"))

    response: Response = auth_client.post(
        f"/moderation/accounts/{alice_account.id}/hide-images",
        json={"reason": "Repeated harassment"},
        headers=nina,
    )

    assert response.status_code == 200
    assert response.json() == {"hidden_count": 2, "has_more": False}
    db_session.expire_all()
    assert all(image.status == ImageStatus.HIDDEN for image in visible)
    assert bob_image.status == ImageStatus.VISIBLE
    entries: list[ModerationAction] = list(db_session.scalars(select(ModerationAction)).all())
    assert {entry.target_id for entry in entries} == {image.id for image in visible}
    assert len(entries) == len(visible)
    assert {(entry.action, entry.reason) for entry in entries} == {
        (ModerationActionKind.HIDE, "Repeated harassment")
    }

    again: Response = auth_client.post(
        f"/moderation/accounts/{alice_account.id}/hide-images",
        json={"reason": "Repeated harassment"},
        headers=nina,
    )

    assert again.json() == {"hidden_count": 0, "has_more": False}


def test_hiding_all_the_images_works_by_batches_until_none_is_left(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
    nina: dict[str, str],
    alice: dict[str, str],
):
    alice_account: User = account(db_session, "alice@example.com")
    visible: list[Image] = [add_image(db_session, stored_images, alice_account) for _ in range(2)]
    monkeypatch.setattr(account_review_module, "HIDE_ALL_IMAGES_BATCH_SIZE", 1)

    def hide_a_batch() -> Response:
        return auth_client.post(
            f"/moderation/accounts/{alice_account.id}/hide-images",
            json={"reason": "Spam"},
            headers=nina,
        )

    assert hide_a_batch().json() == {"hidden_count": 1, "has_more": True}
    assert hide_a_batch().json() == {"hidden_count": 1, "has_more": False}
    db_session.expire_all()
    assert all(image.status == ImageStatus.HIDDEN for image in visible)


def test_hiding_all_the_images_skips_an_image_purged_meanwhile(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
    nina: dict[str, str],
    alice: dict[str, str],
):
    alice_account: User = account(db_session, "alice@example.com")
    visible: Image = add_image(db_session, stored_images, alice_account)
    monkeypatch.setattr(
        image_repository,
        "list_visible_image_ids_of_owner",
        lambda _session, _owner_id, _limit: [uuid.UUID(UNKNOWN_ID), visible.id],
    )

    response: Response = auth_client.post(
        f"/moderation/accounts/{alice_account.id}/hide-images",
        json={"reason": "Spam"},
        headers=nina,
    )

    assert response.status_code == 200
    assert response.json() == {"hidden_count": 1, "has_more": False}
    db_session.expire_all()
    assert visible.status == ImageStatus.HIDDEN


def test_hiding_all_the_images_of_an_unknown_account_is_not_found(
    auth_client: TestClient, nina: dict[str, str]
):
    response: Response = auth_client.post(
        f"/moderation/accounts/{uuid.uuid4()}/hide-images",
        json={"reason": "Spam"},
        headers=nina,
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ACCOUNT_NOT_FOUND


def test_the_recent_uploads_can_show_one_author_with_its_id(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
):
    alice_account: User = account(db_session, "alice@example.com")
    alice_image: Image = add_image(db_session, stored_images, alice_account)
    add_image(db_session, stored_images, account(db_session, "bob@example.com"))

    response: Response = auth_client.get(
        "/moderation/images", params={"owner_id": str(alice_account.id)}, headers=nina
    )

    [listed] = response.json()["images"]
    assert (listed["id"], listed["author_id"]) == (str(alice_image.id), str(alice_account.id))


def test_the_log_can_show_the_decisions_about_an_account_and_its_content(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
):
    nina_account: User = account(db_session, "nina@example.com")
    alice_account: User = account(db_session, "alice@example.com")
    template_id: str = create_template(auth_client, db_session, alice)
    image: Image = add_image(db_session, stored_images, alice_account)
    log_entry(db_session, nina_account, alice_account.id, "a")
    log_entry(db_session, nina_account, uuid.UUID(template_id), "bb")
    log_entry(db_session, nina_account, image.id, "ccc")
    log_entry(db_session, nina_account, account(db_session, "bob@example.com").id, "dddd")
    log_entry(db_session, nina_account, None, "eeeee")

    response: Response = auth_client.get(
        "/moderation/log", params={"account_id": str(alice_account.id)}, headers=nina
    )

    assert [entry["target_label"] for entry in response.json()["entries"]] == ["a", "bb", "ccc"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/moderation/accounts"),
        ("GET", f"/moderation/accounts/{UNKNOWN_ID}"),
        ("POST", f"/moderation/accounts/{UNKNOWN_ID}/hide-images"),
    ],
)
def test_the_account_routes_require_a_super_admin(
    auth_client: TestClient, alice: dict[str, str], method: str, path: str
):
    without_session: Response = auth_client.request(method, path, json={"reason": "Spam"})
    other_account: Response = auth_client.request(
        method, path, json={"reason": "Spam"}, headers=alice
    )

    assert without_session.status_code == 401
    assert other_account.status_code == 403
    assert other_account.json()["code"] == ErrorCode.SUPER_ADMIN_REQUIRED
