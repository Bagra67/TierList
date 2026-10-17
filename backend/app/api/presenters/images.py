"""Adresse publique des images, la même pour toutes les réponses de l'API."""

from app.models.image import Image
from app.services.image_storage import ImageStorage


def image_url(storage: ImageStorage, image: Image) -> str:
    """Adresse publique de l'image dans le bucket. Elle dépend des réglages du stockage, pas du
    modèle : elle est calculée à chaque réponse."""
    return storage.url(image.storage_key)


def optional_image_url(storage: ImageStorage, image: Image | None) -> str | None:
    """Adresse publique de l'image d'une tuile, None pour une tuile qui n'a qu'un texte."""
    if image is None:
        return None
    return image_url(storage, image)
