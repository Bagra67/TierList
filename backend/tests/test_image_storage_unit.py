from typing import Any, cast

from app.services.image_storage import ImageStorage


class RecordingS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []
        self.copy_calls: list[dict[str, Any]] = []
        self.presign_calls: list[tuple[str, dict[str, Any]]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.put_calls.append(kwargs)

    def copy_object(self, **kwargs: Any) -> None:
        self.copy_calls.append(kwargs)

    def generate_presigned_url(self, client_method: str, **kwargs: Any) -> str:
        self.presign_calls.append((client_method, kwargs))
        return "https://s3.example.com/signed"


def test_a_saved_image_is_sent_public_with_its_type_and_cache():
    client: RecordingS3Client = RecordingS3Client()
    storage: ImageStorage = ImageStorage(cast(Any, client), "images", "https://cdn.example.com/")

    storage.save("abc.webp", b"webp")

    assert client.put_calls == [
        {
            "Bucket": "images",
            "Key": "abc.webp",
            "Body": b"webp",
            "ContentType": "image/webp",
            "CacheControl": "public, max-age=86400",
            "ACL": "public-read",
        }
    ]
    assert storage.url("abc.webp") == "https://cdn.example.com/abc.webp"


def test_a_hidden_image_is_copied_private_under_the_quarantine_prefix():
    client: RecordingS3Client = RecordingS3Client()
    storage: ImageStorage = ImageStorage(cast(Any, client), "images", "https://cdn.example.com/")

    storage.copy_to_quarantine("abc.webp")

    assert client.copy_calls == [
        {
            "Bucket": "images",
            "Key": "quarantine/abc.webp",
            "CopySource": {"Bucket": "images", "Key": "abc.webp"},
            "ACL": "private",
        }
    ]


def test_an_unhidden_image_is_copied_back_public_with_its_type_and_cache():
    client: RecordingS3Client = RecordingS3Client()
    storage: ImageStorage = ImageStorage(cast(Any, client), "images", "https://cdn.example.com/")

    storage.copy_from_quarantine("abc.webp")

    assert client.copy_calls == [
        {
            "Bucket": "images",
            "Key": "abc.webp",
            "CopySource": {"Bucket": "images", "Key": "quarantine/abc.webp"},
            "ContentType": "image/webp",
            "CacheControl": "public, max-age=86400",
            "MetadataDirective": "REPLACE",
            "ACL": "public-read",
        }
    ]


def test_a_preview_url_signs_a_read_of_the_key_for_fifteen_minutes():
    client: RecordingS3Client = RecordingS3Client()
    storage: ImageStorage = ImageStorage(cast(Any, client), "images", "https://cdn.example.com/")

    url: str = storage.presigned_url("quarantine/abc.webp")

    assert url == "https://s3.example.com/signed"
    assert client.presign_calls == [
        (
            "get_object",
            {"Params": {"Bucket": "images", "Key": "quarantine/abc.webp"}, "ExpiresIn": 900},
        )
    ]
