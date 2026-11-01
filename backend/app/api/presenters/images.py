"""Adresse publique des images, la même pour toutes les réponses de l'API."""

from app.models.image import Image, ImageStatus
from app.schemas.moderation import RecentUploadResponse
from app.services.image_storage import ImageStorage, quarantine_key
from app.services.recent_uploads import RecentUpload


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


def recent_upload_response(storage: ImageStorage, upload: RecentUpload) -> RecentUploadResponse:
    """Une image des derniers envois. Une image masquée n'est plus à son adresse publique : le
    super admin la voit par une adresse signée et temporaire de sa quarantaine, qui reste
    privée."""
    image: Image = upload.image
    url: str = (
        storage.presigned_url(quarantine_key(image.storage_key))
        if image.status == ImageStatus.HIDDEN
        else image_url(storage, image)
    )
    return RecentUploadResponse(
        id=image.id,
        url=url,
        status=image.status,
        created_at=image.created_at,
        author_name=upload.author_name,
        template_names=upload.template_names,
        game_count=upload.game_count,
    )
