"""Adresse publique des images, la même pour toutes les réponses de l'API."""

from app.models.image import Image, ImageStatus
from app.services.image_storage import ImageStorage


def image_url(storage: ImageStorage, image: Image) -> str:
    """Adresse publique de l'image dans le bucket. Elle dépend des réglages du stockage, pas du
    modèle : elle est calculée à chaque réponse."""
    return storage.url(image.storage_key)


def optional_image_url(storage: ImageStorage, image: Image | None) -> str | None:
    """Adresse publique de l'image d'une tuile, None pour une tuile qui n'a qu'un texte ou dont
    l'image est retirée par la modération : son fichier n'est plus à cette adresse."""
    if image is None or is_image_removed(image):
        return None
    return image_url(storage, image)


def is_image_removed(image: Image | None) -> bool:
    """L'image de la tuile est masquée ou supprimée par la modération : le frontend montre un
    visuel « image retirée » à sa place (US-1.4)."""
    return image is not None and image.status != ImageStatus.VISIBLE
