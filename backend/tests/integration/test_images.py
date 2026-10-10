import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from PIL import Image as PillowImage
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.image import Image, ImageStatus
from tests.image_files import make_image_file
from tests.integration.conftest import FAKE_IMAGE_BASE_URL

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"

JsonObject = dict[str, Any]


def register(client: TestClient, email: str) -> dict[str, str]:
    """Crée un compte et renvoie l'en-tête Authorization de son access token."""
    response: Response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


def upload(
    client: TestClient,
    headers: dict[str, str],
    content: bytes,
    filename: str = "photo.png",
    content_type: str = "image/png",
) -> Response:
    return client.post(
        "/images", files={"file": (filename, content, content_type)}, headers=headers
    )


def test_upload_compresses_and_stores_the_image(
    auth_client: TestClient,
    alice: dict[str, str],
    db_session: Session,
    stored_images: dict[str, bytes],
):
    content: bytes = make_image_file((1000, 500), "PNG")

    response: Response = upload(auth_client, alice, content)

    assert response.status_code == 201
    body: JsonObject = response.json()
    assert (body["width"], body["height"]) == (512, 256)
    image: Image | None = db_session.get(Image, uuid.UUID(body["id"]))
    assert image is not None
    assert body["url"] == f"{FAKE_IMAGE_BASE_URL}/{image.storage_key}"
    assert image.storage_key.endswith(".webp")
    assert image.sha256 == hashlib.sha256(content).hexdigest()
    assert image.status == ImageStatus.VISIBLE
    stored: bytes = stored_images[image.storage_key]
    assert image.size_bytes == len(stored)
    assert PillowImage.open(BytesIO(stored)).format == "WEBP"


def test_each_upload_gets_a_new_storage_key(
    auth_client: TestClient, alice: dict[str, str], stored_images: dict[str, bytes]
):
    content: bytes = make_image_file((100, 100), "PNG")

    first: Response = upload(auth_client, alice, content)
    second: Response = upload(auth_client, alice, content)

    assert first.json()["id"] != second.json()["id"]
    assert first.json()["url"] != second.json()["url"]
    assert len(stored_images) == 2


def test_a_failed_database_save_leaves_no_file_in_the_storage(
    auth_client: TestClient,
    alice: dict[str, str],
    db_session: Session,
    stored_images: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_commit() -> None:
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    monkeypatch.setattr(db_session, "commit", fail_commit)

    response: Response = upload(auth_client, alice, make_image_file((100, 100), "PNG"))

    assert response.status_code == 500
    assert stored_images == {}


def test_deleting_the_account_keeps_its_images_for_the_garbage_collection(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    uploaded: Response = upload(auth_client, alice, make_image_file((100, 100), "PNG"))

    # TestClient.delete n'accepte pas de corps : on passe par request()
    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=alice
    )

    assert deleted.status_code == 204
    image: Image | None = db_session.get(Image, uuid.UUID(uploaded.json()["id"]))
    assert image is not None
    db_session.refresh(image)
    assert image.owner_id is None


def test_the_format_is_read_from_the_content_not_the_name_or_type(
    auth_client: TestClient, alice: dict[str, str]
):
    png_named_like_svg: Response = upload(
        auth_client,
        alice,
        make_image_file((100, 100), "PNG"),
        filename="drawing.svg",
        content_type="image/svg+xml",
    )
    svg_named_like_png: Response = upload(
        auth_client, alice, b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    )

    assert png_named_like_svg.status_code == 201
    assert svg_named_like_png.status_code == 415
    assert svg_named_like_png.json()["code"] == ErrorCode.IMAGE_UNSUPPORTED_FORMAT


def test_upload_refuses_a_gif(
    auth_client: TestClient, alice: dict[str, str], stored_images: dict[str, bytes]
):
    response: Response = upload(
        auth_client,
        alice,
        make_image_file((100, 100), "GIF"),
        filename="anim.gif",
        content_type="image/gif",
    )

    assert response.status_code == 415
    assert response.json()["code"] == ErrorCode.IMAGE_UNSUPPORTED_FORMAT
    assert stored_images == {}


def test_upload_refuses_a_file_over_the_size_limit(
    auth_client: TestClient,
    alice: dict[str, str],
    override_settings: Callable[..., None],
    stored_images: dict[str, bytes],
):
    content: bytes = make_image_file((100, 100), "PNG")
    override_settings(image_upload_max_bytes=len(content) - 1)

    response: Response = upload(auth_client, alice, content)

    assert response.status_code == 413
    body: JsonObject = response.json()
    assert body["code"] == ErrorCode.IMAGE_TOO_LARGE
    assert body["params"] == {"max_bytes": len(content) - 1}
    assert stored_images == {}


def test_upload_accepts_a_file_at_the_size_limit(
    auth_client: TestClient, alice: dict[str, str], override_settings: Callable[..., None]
):
    content: bytes = make_image_file((100, 100), "PNG")
    override_settings(image_upload_max_bytes=len(content))

    response: Response = upload(auth_client, alice, content)

    assert response.status_code == 201


def test_upload_refuses_an_image_with_too_many_pixels(
    auth_client: TestClient,
    alice: dict[str, str],
    override_settings: Callable[..., None],
    stored_images: dict[str, bytes],
):
    override_settings(image_max_source_pixels=100 * 100 - 1)

    response: Response = upload(auth_client, alice, make_image_file((100, 100), "PNG"))

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.IMAGE_TOO_MANY_PIXELS
    assert stored_images == {}


def test_uploads_are_limited_per_account_and_hour(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    override_settings: Callable[..., None],
    stored_images: dict[str, bytes],
):
    override_settings(image_uploads_per_hour_max=2)
    content: bytes = make_image_file((100, 100), "PNG")
    for _ in range(2):
        assert upload(auth_client, alice, content).status_code == 201

    refused: Response = upload(auth_client, alice, content)

    assert refused.status_code == 429
    body: JsonObject = refused.json()
    assert body["code"] == ErrorCode.IMAGE_UPLOAD_LIMIT_REACHED
    assert body["params"] == {"max_uploads": 2}
    assert len(stored_images) == 2
    # La limite est propre à chaque compte
    assert upload(auth_client, bob, content).status_code == 201


def test_uploads_older_than_an_hour_do_not_count(
    auth_client: TestClient,
    alice: dict[str, str],
    db_session: Session,
    override_settings: Callable[..., None],
):
    override_settings(image_uploads_per_hour_max=1)
    content: bytes = make_image_file((100, 100), "PNG")
    first: Response = upload(auth_client, alice, content)
    db_session.execute(
        update(Image)
        .where(Image.id == uuid.UUID(first.json()["id"]))
        .values(created_at=datetime.now(UTC) - timedelta(hours=1, minutes=1))
    )

    response: Response = upload(auth_client, alice, content)

    assert response.status_code == 201


def test_upload_without_a_file_is_a_validation_error(
    auth_client: TestClient, alice: dict[str, str]
):
    response: Response = auth_client.post("/images", headers=alice)

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_ERROR


def test_upload_requires_authentication(auth_client: TestClient, stored_images: dict[str, bytes]):
    response: Response = upload(auth_client, {}, make_image_file((100, 100), "PNG"))

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED
    assert stored_images == {}
