"""Envoi des images des tuiles : vérification, compression, stockage (docs/technical/images.md).

Le service possède la frontière de transaction : l'image est enregistrée en base par un commit,
une fois son fichier écrit dans le stockage.
"""

import hashlib
import logging
import uuid
from typing import BinaryIO

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.constants.images import IMAGE_FILE_EXTENSION
from app.core.config import Settings
from app.exceptions.images import ImageTooLargeError
from app.models.image import Image
from app.models.user import User
from app.repositories import images as image_repository
from app.services.image_processing import CompressedImage, compress_image
from app.services.image_storage import ImageStorage

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self, session: Session, settings: Settings, storage: ImageStorage) -> None:
        self._session = session
        self._settings = settings
        self._storage = storage

    def upload(self, owner: User, file: BinaryIO) -> Image:
        """Compresse l'image envoyée et la stocke sous une nouvelle clé aléatoire.

        Lève ImageTooLargeError, ImageUnsupportedFormatError ou ImageTooManyPixelsError.
        """
        content: bytes = self._read_within_limit(file)
        compressed: CompressedImage = compress_image(
            content, self._settings.image_max_source_pixels
        )
        image: Image = Image(
            owner_id=owner.id,
            storage_key=f"{uuid.uuid4()}.{IMAGE_FILE_EXTENSION}",
            width=compressed.width,
            height=compressed.height,
            size_bytes=len(compressed.data),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        self._storage.save(image.storage_key, compressed.data)
        image_repository.add_image(self._session, image)
        try:
            self._session.commit()
        except SQLAlchemyError:
            # Sans ligne en base, aucun nettoyage ne retrouverait le fichier : il est retiré ici
            self._session.rollback()
            self._storage.delete(image.storage_key)
            raise
        logger.info(
            "Image envoyée : image_id=%s owner_id=%s size_bytes=%d",
            image.id,
            owner.id,
            image.size_bytes,
        )
        return image

    def url(self, image: Image) -> str:
        return self._storage.url(image.storage_key)

    def _read_within_limit(self, file: BinaryIO) -> bytes:
        """Lit le fichier sans jamais dépasser la limite d'un octet : un fichier énorme n'est
        pas chargé en mémoire."""
        max_bytes: int = self._settings.image_upload_max_bytes
        content: bytes = file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ImageTooLargeError(max_bytes)
        return content
