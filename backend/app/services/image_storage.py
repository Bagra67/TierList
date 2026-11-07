from functools import lru_cache
from typing import TYPE_CHECKING

lazy import boto3
lazy from botocore.config import Config

from app.constants.images import (
    IMAGE_ACL,
    IMAGE_CACHE_CONTROL,
    IMAGE_CONTENT_TYPE,
    IMAGE_PREVIEW_URL_EXPIRES_SECONDS,
    IMAGE_QUARANTINE_ACL,
    IMAGE_QUARANTINE_PREFIX,
)
from app.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class ImageStorage:
    def __init__(self, client: S3Client, bucket: str, public_base_url: str) -> None:
        self._client = client
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")

    def save(self, key: str, data: bytes) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=IMAGE_CONTENT_TYPE,
            CacheControl=IMAGE_CACHE_CONTROL,
            ACL=IMAGE_ACL,
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def copy_to_quarantine(self, key: str) -> None:
        self._client.copy_object(
            Bucket=self._bucket,
            Key=quarantine_key(key),
            CopySource={"Bucket": self._bucket, "Key": key},
            ACL=IMAGE_QUARANTINE_ACL,
        )

    def copy_from_quarantine(self, key: str) -> None:
        self._client.copy_object(
            Bucket=self._bucket,
            Key=key,
            CopySource={"Bucket": self._bucket, "Key": quarantine_key(key)},
            ContentType=IMAGE_CONTENT_TYPE,
            CacheControl=IMAGE_CACHE_CONTROL,
            MetadataDirective="REPLACE",
            ACL=IMAGE_ACL,
        )

    def presigned_url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=IMAGE_PREVIEW_URL_EXPIRES_SECONDS,
        )

    def url(self, key: str) -> str:
        return f"{self._public_base_url}/{key}"


def quarantine_key(key: str) -> str:
    return f"{IMAGE_QUARANTINE_PREFIX}/{key}"


def create_image_storage(settings: Settings) -> ImageStorage:
    secret_access_key: str | None = None
    if settings.image_s3_secret_access_key is not None:
        secret_access_key = settings.image_s3_secret_access_key.get_secret_value()
    client: S3Client = _shared_s3_client_for_configuration(
        settings.image_s3_endpoint_url,
        settings.image_s3_region,
        settings.image_s3_access_key_id,
        secret_access_key,
        settings.image_s3_timeout_seconds,
    )
    return ImageStorage(client, settings.image_s3_bucket, settings.image_public_base_url)


@lru_cache
def _shared_s3_client_for_configuration(
    endpoint_url: str | None,
    region: str,
    access_key_id: str | None,
    secret_access_key: str | None,
    timeout_seconds: int,
) -> S3Client:
    config: Config = Config(
        connect_timeout=timeout_seconds,
        read_timeout=timeout_seconds,
        retries={"max_attempts": 2, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=config,
    )
