"""Stockage S3 réel (SeaweedFS en local et en CI) : écriture, lecture publique, suppression."""

import uuid

import httpx
import pytest

from app.constants.images import IMAGE_CACHE_CONTROL, IMAGE_CONTENT_TYPE
from app.services.image_storage import ImageStorage

pytestmark = pytest.mark.integration

HTTP_TIMEOUT_SECONDS: float = 10


def test_a_saved_image_is_publicly_readable_with_long_caching(s3_image_storage: ImageStorage):
    key: str = f"test-{uuid.uuid4()}.webp"
    data: bytes = b"RIFF\x00\x00\x00\x00WEBPtest"

    s3_image_storage.save(key, data)
    try:
        # Sans authentification : l'URL publique suffit (lien public des résultats)
        response: httpx.Response = httpx.get(
            s3_image_storage.url(key), timeout=HTTP_TIMEOUT_SECONDS
        )
    finally:
        s3_image_storage.delete(key)

    assert response.status_code == 200
    assert response.content == data
    assert response.headers["content-type"] == IMAGE_CONTENT_TYPE
    assert response.headers["cache-control"] == IMAGE_CACHE_CONTROL


def test_a_deleted_image_is_no_longer_readable(s3_image_storage: ImageStorage):
    key: str = f"test-{uuid.uuid4()}.webp"
    s3_image_storage.save(key, b"RIFF\x00\x00\x00\x00WEBPtest")

    s3_image_storage.delete(key)

    response: httpx.Response = httpx.get(s3_image_storage.url(key), timeout=HTTP_TIMEOUT_SECONDS)
    assert response.status_code == 404


def test_the_bucket_cannot_be_written_anonymously(s3_image_storage: ImageStorage):
    key: str = f"test-{uuid.uuid4()}.webp"

    response: httpx.Response = httpx.put(
        s3_image_storage.url(key), content=b"not allowed", timeout=HTTP_TIMEOUT_SECONDS
    )

    assert response.status_code == 403
