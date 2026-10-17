"""Adresse publique des images, la même pour toutes les réponses de l'API."""

from typing import overload

from app.models.image import Image
from app.services.image_storage import ImageStorage


@overload
def image_url(storage: ImageStorage, image: Image) -> str: ...
@overload
def image_url(storage: ImageStorage, image: None) -> None: ...
@overload
def image_url(storage: ImageStorage, image: Image | None) -> str | None: ...
def image_url(storage: ImageStorage, image: Image | None) -> str | None:
    """Adresse publique de l'image dans le bucket, None sans image. Elle dépend des réglages du
    stockage, pas du modèle : elle est calculée à chaque réponse."""
    if image is None:
        return None
    return storage.url(image.storage_key)
