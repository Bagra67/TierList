"""Stockage des images dans un bucket S3 (docs/technical/images.md, « Storage and serving »).

L'API S3 est utilisée partout : SeaweedFS en développement et en CI, un fournisseur compatible S3
en production. Changer de fournisseur ne demande que des réglages IMAGE_S3_*.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from app.constants.images import IMAGE_CACHE_CONTROL, IMAGE_CONTENT_TYPE
from app.core.config import Settings

if TYPE_CHECKING:
    # Types du client S3 (boto3-stubs) : dépendance de développement, absente en production
    from mypy_boto3_s3 import S3Client


class ImageStorage:
    def __init__(self, client: "S3Client", bucket: str, public_base_url: str) -> None:
        self._client = client
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")

    def save(self, key: str, data: bytes) -> None:
        """Écrit l'image sous cette clé. Une clé n'est jamais réécrite : son contenu peut rester
        en cache sans limite de durée."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=IMAGE_CONTENT_TYPE,
            CacheControl=IMAGE_CACHE_CONTROL,
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def url(self, key: str) -> str:
        """Adresse publique de l'image, lisible sans authentification."""
        return f"{self._public_base_url}/{key}"


def create_image_storage(settings: Settings) -> ImageStorage:
    secret_access_key: str | None = None
    if settings.image_s3_secret_access_key is not None:
        secret_access_key = settings.image_s3_secret_access_key.get_secret_value()
    client: S3Client = _create_s3_client(
        settings.image_s3_endpoint_url,
        settings.image_s3_region,
        settings.image_s3_access_key_id,
        secret_access_key,
        settings.image_s3_timeout_seconds,
    )
    return ImageStorage(client, settings.image_s3_bucket, settings.image_public_base_url)


# Créer un client boto3 est coûteux (lecture des définitions de l'API) : un client par
# configuration est gardé et partagé entre les requêtes (les clients boto3 sont thread-safe)
@lru_cache
def _create_s3_client(
    endpoint_url: str | None,
    region: str,
    access_key_id: str | None,
    secret_access_key: str | None,
    timeout_seconds: int,
) -> "S3Client":
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
