import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_image_storage
from app.constants.error_codes import ErrorCode
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.main import api_app
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.user import User
from app.services.image_storage import quarantine_key
from tests.integration.conftest import FailingImageStorage
from tests.integration.helpers import register, register_super_admin

pytestmark = pytest.mark.integration

IMAGE_ACTIONS: tuple[str, ...] = ("hide", "unhide", "delete")
FILE_CONTENT: bytes = b"webp"


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


def add_image(db_session: Session, stored_images: dict[str, bytes], status: ImageStatus) -> Image:
    owner: User = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    image: Image = Image(
        owner_id=owner.id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=len(FILE_CONTENT),
        sha256="a" * 64,
        status=status,
    )
    db_session.add(image)
    db_session.flush()
    if status == ImageStatus.VISIBLE:
        stored_images[image.storage_key] = FILE_CONTENT
    elif status == ImageStatus.HIDDEN:
        stored_images[quarantine_key(image.storage_key)] = FILE_CONTENT
    return image


def moderate(
    client: TestClient,
    headers: dict[str, str],
    action: str,
    image_id: uuid.UUID,
    reason: str = "Violence",
) -> Response:
    return client.post(
        f"/moderation/images/{image_id}/{action}", json={"reason": reason}, headers=headers
    )


def logged_actions(db_session: Session) -> list[ModerationAction]:
    return list(db_session.scalars(select(ModerationAction)).all())


def test_hiding_an_image_moves_its_file_to_the_quarantine_and_logs_the_action(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
):
    image: Image = add_image(db_session, stored_images, ImageStatus.VISIBLE)

    response: Response = moderate(auth_client, nina, "hide", image.id, "  Violence  ")

    assert response.status_code == 204
    db_session.refresh(image)
    assert image.status == ImageStatus.HIDDEN
    assert stored_images == {quarantine_key(image.storage_key): FILE_CONTENT}
    [entry] = logged_actions(db_session)
    assert (entry.actor_name, entry.action, entry.target_type) == (
        "nina",
        ModerationActionKind.HIDE,
        ModerationTargetType.IMAGE,
    )
    assert (entry.target_id, entry.target_label, entry.reason) == (
        image.id,
        image.storage_key,
        "Violence",
    )


def test_unhiding_an_image_puts_its_file_back_at_its_public_address(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
):
    image: Image = add_image(db_session, stored_images, ImageStatus.HIDDEN)

    response: Response = moderate(auth_client, nina, "unhide", image.id, "Appeal accepted")

    assert response.status_code == 204
    db_session.refresh(image)
    assert image.status == ImageStatus.VISIBLE
    assert stored_images == {image.storage_key: FILE_CONTENT}
    [entry] = logged_actions(db_session)
    assert (entry.action, entry.reason) == (ModerationActionKind.UNHIDE, "Appeal accepted")


@pytest.mark.parametrize("status", [ImageStatus.VISIBLE, ImageStatus.HIDDEN])
def test_deleting_an_image_erases_its_file_and_keeps_its_fingerprint(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    status: ImageStatus,
):
    image: Image = add_image(db_session, stored_images, status)

    response: Response = moderate(auth_client, nina, "delete", image.id)

    assert response.status_code == 204
    db_session.refresh(image)
    assert (image.status, image.sha256) == (ImageStatus.DELETED, "a" * 64)
    assert stored_images == {}
    [entry] = logged_actions(db_session)
    assert entry.action == ModerationActionKind.DELETE


@pytest.mark.parametrize(
    ("action", "status"),
    [
        ("hide", ImageStatus.HIDDEN),
        ("hide", ImageStatus.DELETED),
        ("unhide", ImageStatus.VISIBLE),
        ("unhide", ImageStatus.DELETED),
        ("delete", ImageStatus.DELETED),
    ],
)
def test_an_action_that_does_not_apply_to_the_status_is_refused(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    action: str,
    status: ImageStatus,
):
    image: Image = add_image(db_session, stored_images, status)
    files_before: dict[str, bytes] = dict(stored_images)

    response: Response = moderate(auth_client, nina, action, image.id)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.IMAGE_MODERATION_CONFLICT
    db_session.refresh(image)
    assert image.status == status
    assert stored_images == files_before
    assert logged_actions(db_session) == []


@pytest.mark.parametrize("action", IMAGE_ACTIONS)
def test_an_unknown_image_is_not_found(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], action: str
):
    response: Response = moderate(auth_client, nina, action, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.IMAGE_NOT_FOUND
    assert logged_actions(db_session) == []


@pytest.mark.parametrize("action", IMAGE_ACTIONS)
def test_the_image_actions_require_a_session(auth_client: TestClient, action: str):
    response: Response = auth_client.post(
        f"/moderation/images/{uuid.uuid4()}/{action}", json={"reason": "Violence"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


@pytest.mark.parametrize("action", IMAGE_ACTIONS)
def test_the_image_actions_refuse_other_accounts(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    alice: dict[str, str],
    action: str,
):
    image: Image = add_image(db_session, stored_images, ImageStatus.VISIBLE)

    response: Response = moderate(auth_client, alice, action, image.id)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.SUPER_ADMIN_REQUIRED
    db_session.refresh(image)
    assert image.status == ImageStatus.VISIBLE


@pytest.mark.parametrize("reason", ["", "   ", "x" * (MODERATION_REASON_MAX_LENGTH + 1)])
def test_an_action_needs_a_reason_of_at_most_500_characters(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    reason: str,
):
    image: Image = add_image(db_session, stored_images, ImageStatus.VISIBLE)

    response: Response = moderate(auth_client, nina, "hide", image.id, reason)

    assert response.status_code == 422
    db_session.refresh(image)
    assert image.status == ImageStatus.VISIBLE


def test_a_failed_database_save_leaves_the_image_public_without_a_quarantine_copy(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    image: Image = add_image(db_session, stored_images, ImageStatus.VISIBLE)
    storage_key: str = image.storage_key

    def fail_commit() -> None:
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    monkeypatch.setattr(db_session, "commit", fail_commit)

    response: Response = moderate(auth_client, nina, "hide", image.id)

    assert response.status_code == 500
    assert stored_images == {storage_key: FILE_CONTENT}


def test_a_public_file_that_cannot_be_erased_after_hiding_is_logged_with_its_key(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    caplog: pytest.LogCaptureFixture,
):
    image: Image = add_image(db_session, stored_images, ImageStatus.VISIBLE)
    failing_storage: FailingImageStorage = FailingImageStorage(stored_images, image.storage_key)
    api_app.dependency_overrides[get_image_storage] = lambda: failing_storage

    with caplog.at_level(logging.ERROR):
        response: Response = moderate(auth_client, nina, "hide", image.id)

    assert response.status_code == 204
    db_session.refresh(image)
    assert image.status == ImageStatus.HIDDEN
    assert image.storage_key in caplog.text
