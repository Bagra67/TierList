"""Envoi des images des tuiles : vérification, compression, stockage (docs/technical/images.md).

Le service possède la frontière de transaction : l'image est enregistrée en base par un commit,
une fois son fichier écrit dans le stockage.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import BinaryIO

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.constants.images import IMAGE_FILE_EXTENSION
from app.core.config import Settings
from app.exceptions.images import ImageTooLargeError, ImageUploadLimitReachedError
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

        Lève ImageUploadLimitReachedError, ImageTooLargeError, ImageUnsupportedFormatError ou
        ImageTooManyPixelsError.
        """
        self._check_upload_limit(owner)
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

    def purge_unused(self) -> int:
        """Ramasse-miettes : efface les images qu'aucune tuile n'utilise depuis plus que la durée
        de conservation (envois abandonnés, tuiles modifiées ou supprimées, templates purgés,
        comptes supprimés) ; renvoie leur nombre.

        Les lignes sont supprimées d'abord, puis les fichiers : un fichier qu'on n'arrive pas
        à effacer est seulement journalisé, aucune tuile ne pointe jamais vers un fichier
        absent. Les instantanés de partie, quand ils existeront, devront aussi garder leurs
        images (docs/technical/images.md, « Cleanup »)."""
        limit: datetime = datetime.now(UTC) - timedelta(
            days=self._settings.unused_image_retention_days
        )
        storage_keys: list[str] = image_repository.delete_unused_images_created_before(
            self._session, limit
        )
        self._session.commit()
        for storage_key in storage_keys:
            try:
                self._storage.delete(storage_key)
            except (BotoCoreError, ClientError):
                # La clé permet d'effacer le fichier à la main ; le prochain passage ne le
                # retrouvera pas, sa ligne n'existant plus
                logger.exception("Fichier d'image non effacé : storage_key=%s", storage_key)
        logger.info(
            "Images inutilisées purgées : %d (créées avant %s)",
            len(storage_keys),
            limit.isoformat(),
        )
        return len(storage_keys)

    def _check_upload_limit(self, owner: User) -> None:
        """Refuse l'envoi au-delà de IMAGE_UPLOADS_PER_HOUR_MAX images sur l'heure écoulée.

        Deux envois simultanés peuvent dépasser la limite d'une image : elle sert à freiner
        les abus, pas à compter au plus juste."""
        max_uploads: int = self._settings.image_uploads_per_hour_max
        since: datetime = datetime.now(UTC) - timedelta(hours=1)
        recent_uploads: int = image_repository.count_images_created_since(
            self._session, owner.id, since
        )
        if recent_uploads >= max_uploads:
            raise ImageUploadLimitReachedError(max_uploads)

    def _read_within_limit(self, file: BinaryIO) -> bytes:
        """Lit le fichier sans jamais dépasser la limite d'un octet : un fichier énorme n'est
        pas chargé en mémoire."""
        max_bytes: int = self._settings.image_upload_max_bytes
        content: bytes = file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ImageTooLargeError(max_bytes)
        return content
