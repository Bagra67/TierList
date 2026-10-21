from typing import Any

from fastapi import APIRouter, UploadFile

from app.api.dependencies import (
    CurrentUserDep,
    ImageServiceDep,
    ImageStorageDep,
)
from app.api.presenters.images import image_url
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.images import (
    ImageTooLargeError,
    ImageTooManyPixelsError,
    ImageUnsupportedFormatError,
    ImageUploadLimitReachedError,
)
from app.models.image import Image
from app.schemas.images import ImageUploadResponse

router = APIRouter(prefix="/images", tags=["images"])

UPLOAD_IMAGE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    413: {"model": ErrorResponse, "description": messages.IMAGE_TOO_LARGE_DESCRIPTION},
    415: {"model": ErrorResponse, "description": messages.IMAGE_UNSUPPORTED_FORMAT_DESCRIPTION},
    422: {"model": ErrorResponse, "description": messages.IMAGE_TOO_MANY_PIXELS_DESCRIPTION},
    429: {"model": ErrorResponse, "description": messages.IMAGE_UPLOAD_LIMIT_REACHED_DESCRIPTION},
}


# def et non async def : la compression utilise le processeur, FastAPI exécute donc la route dans
# son pool de threads sans bloquer la boucle d'événements
@router.post("", status_code=201, responses=UPLOAD_IMAGE_RESPONSES)
def upload_image(
    file: UploadFile,
    user: CurrentUserDep,
    service: ImageServiceDep,
    storage: ImageStorageDep,
) -> ImageUploadResponse:
    """Envoie une image de tuile (JPEG, PNG ou WebP), compressée en WebP par le serveur."""
    try:
        image: Image = service.upload(user, file.file)
    except ImageUploadLimitReachedError as exc:
        raise AppHTTPException(
            status_code=429,
            code=ErrorCode.IMAGE_UPLOAD_LIMIT_REACHED,
            detail=messages.IMAGE_UPLOAD_LIMIT_REACHED.format(max_uploads=exc.max_uploads),
            params={"max_uploads": exc.max_uploads},
        ) from exc
    except ImageTooLargeError as exc:
        # La limite part en param : le frontend l'affiche sans la recopier dans ses traductions
        raise AppHTTPException(
            status_code=413,
            code=ErrorCode.IMAGE_TOO_LARGE,
            detail=messages.IMAGE_TOO_LARGE.format(max_bytes=exc.max_bytes),
            params={"max_bytes": exc.max_bytes},
        ) from exc
    except ImageUnsupportedFormatError as exc:
        raise AppHTTPException(
            status_code=415,
            code=ErrorCode.IMAGE_UNSUPPORTED_FORMAT,
            detail=messages.IMAGE_UNSUPPORTED_FORMAT,
        ) from exc
    except ImageTooManyPixelsError as exc:
        raise AppHTTPException(
            status_code=422,
            code=ErrorCode.IMAGE_TOO_MANY_PIXELS,
            detail=messages.IMAGE_TOO_MANY_PIXELS,
        ) from exc
    return ImageUploadResponse(
        id=image.id, url=image_url(storage, image), width=image.width, height=image.height
    )
