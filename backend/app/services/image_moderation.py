import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
lazy from botocore.exceptions import BotoCoreError, ClientError

from app.exceptions.images import ImageModerationConflictError, ImageNotFoundError
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.image import Image, ImageStatus
from app.models.user import User
from app.repositories import images as image_repository
from app.services.image_storage import ImageStorage, quarantine_key
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)


class ImageModerationService:
    def __init__(
        self, session: Session, storage: ImageStorage, moderation_log: ModerationLogService
    ) -> None:
        self._session = session
        self._storage = storage
        self._moderation_log = moderation_log

    def hide(self, super_admin: User, image_id: uuid.UUID, reason: str) -> None:
        image: Image = self._lock_image(image_id)
        if image.status != ImageStatus.VISIBLE:
            raise ImageModerationConflictError
        storage_key: str = image.storage_key
        self._storage.copy_to_quarantine(storage_key)
        image.status = ImageStatus.HIDDEN
        self._commit_action(
            super_admin, ModerationActionKind.HIDE, image, reason, quarantine_key(storage_key)
        )
        self._delete_file(storage_key)
        logger.info("Image masquée : image_id=%s super_admin_id=%s", image_id, super_admin.id)

    def unhide(self, super_admin: User, image_id: uuid.UUID, reason: str) -> None:
        image: Image = self._lock_image(image_id)
        if image.status != ImageStatus.HIDDEN:
            raise ImageModerationConflictError
        storage_key: str = image.storage_key
        self._storage.copy_from_quarantine(storage_key)
        image.status = ImageStatus.VISIBLE
        self._commit_action(super_admin, ModerationActionKind.UNHIDE, image, reason, storage_key)
        self._delete_file(quarantine_key(storage_key))
        logger.info("Image réaffichée : image_id=%s super_admin_id=%s", image_id, super_admin.id)

    def delete(self, super_admin: User, image_id: uuid.UUID, reason: str) -> None:
        image: Image = self._lock_image(image_id)
        if image.status == ImageStatus.DELETED:
            raise ImageModerationConflictError
        file_key: str = (
            quarantine_key(image.storage_key)
            if image.status == ImageStatus.HIDDEN
            else image.storage_key
        )
        image.status = ImageStatus.DELETED
        self._commit_action(super_admin, ModerationActionKind.DELETE, image, reason, None)
        self._delete_file(file_key)
        logger.info("Image supprimée : image_id=%s super_admin_id=%s", image_id, super_admin.id)

    def _lock_image(self, image_id: uuid.UUID) -> Image:
        image: Image | None = image_repository.get_image_for_update(self._session, image_id)
        if image is None:
            raise ImageNotFoundError
        return image

    def _commit_action(
        self,
        super_admin: User,
        action: ModerationActionKind,
        image: Image,
        reason: str,
        copied_key: str | None,
    ) -> None:
        try:
            self._moderation_log.record(
                super_admin,
                action,
                ModerationTargetType.IMAGE,
                image.id,
                image.storage_key,
                reason,
            )
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            if copied_key is not None:
                self._delete_file(copied_key)
            raise

    def _delete_file(self, key: str) -> None:
        try:
            self._storage.delete(key)
        except BotoCoreError, ClientError:
            logger.exception("Fichier d'image non effacé : storage_key=%s", key)
