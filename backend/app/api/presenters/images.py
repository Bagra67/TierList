from app.models.image import Image, ImageStatus
from app.schemas.moderation import RecentUploadResponse
from app.services.image_storage import ImageStorage, quarantine_key
from app.services.recent_uploads import RecentUpload


def image_url(storage: ImageStorage, image: Image) -> str:
    return storage.url(image.storage_key)


def optional_image_url(storage: ImageStorage, image: Image | None) -> str | None:
    if image is None or is_image_removed(image):
        return None
    return image_url(storage, image)


def is_image_removed(image: Image | None) -> bool:
    return image is not None and image.status != ImageStatus.VISIBLE


def image_url_for_super_admin(storage: ImageStorage, image: Image) -> str:
    return (
        storage.presigned_url(quarantine_key(image.storage_key))
        if image.status == ImageStatus.HIDDEN
        else image_url(storage, image)
    )


def recent_upload_response(storage: ImageStorage, upload: RecentUpload) -> RecentUploadResponse:
    image: Image = upload.image
    url: str = image_url_for_super_admin(storage, image)
    return RecentUploadResponse(
        id=image.id,
        url=url,
        status=image.status,
        created_at=image.created_at,
        author_id=image.owner_id,
        author_name=upload.author_name,
        template_names=upload.template_names,
        game_count=upload.game_count,
    )
