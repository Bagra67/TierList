"""Modération des images des tuiles (US-1.4, US-1.6, docs/technical/images.md, « Moderation ») :
masquer, réafficher ou supprimer une image.

Les URL des images sont publiques : masquer une image agit sur le stockage, pas seulement sur la
base. L'ordre des étapes échoue du côté sûr : le fichier est d'abord copié à son nouvel
emplacement, le statut et l'entrée du journal sont validés ensemble, puis l'ancien fichier est
effacé. Un effacement qui échoue est journalisé avec sa clé, pour être fait à la main ; l'API ne
donne déjà plus l'adresse d'une image masquée.
"""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Différé (PEP 810) : botocore n'est chargé que si une erreur de stockage survient
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
        """Masque une image visible : son fichier passe en quarantaine, privé, et un visuel
        « image retirée » la remplace partout. Lève ImageNotFoundError ou
        ImageModerationConflictError."""
        image: Image = self._get_image(image_id)
        if image.status != ImageStatus.VISIBLE:
            raise ImageModerationConflictError
        storage_key: str = image.storage_key
        self._storage.copy_to_quarantine(storage_key)
        image.status = ImageStatus.HIDDEN
        # Sans le masquage en base, la copie en quarantaine ne servirait à rien : elle est retirée
        self._commit_action(
            super_admin, ModerationActionKind.HIDE, image, reason, quarantine_key(storage_key)
        )
        self._delete_file(storage_key)
        logger.info("Image masquée : image_id=%s super_admin_id=%s", image_id, super_admin.id)

    def unhide(self, super_admin: User, image_id: uuid.UUID, reason: str) -> None:
        """Réaffiche une image masquée : son fichier revient à son adresse publique. Lève
        ImageNotFoundError ou ImageModerationConflictError."""
        image: Image = self._get_image(image_id)
        if image.status != ImageStatus.HIDDEN:
            raise ImageModerationConflictError
        storage_key: str = image.storage_key
        self._storage.copy_from_quarantine(storage_key)
        image.status = ImageStatus.VISIBLE
        # Sans le réaffichage en base, la copie publique montrerait une image encore masquée
        self._commit_action(super_admin, ModerationActionKind.UNHIDE, image, reason, storage_key)
        self._delete_file(quarantine_key(storage_key))
        logger.info("Image réaffichée : image_id=%s super_admin_id=%s", image_id, super_admin.id)

    def delete(self, super_admin: User, image_id: uuid.UUID, reason: str) -> None:
        """Supprime une image visible ou masquée, définitivement : son fichier est effacé, sa
        ligne garde le statut et l'empreinte, qui refuse le renvoi du même fichier. Lève
        ImageNotFoundError ou ImageModerationConflictError."""
        image: Image = self._get_image(image_id)
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

    def _get_image(self, image_id: uuid.UUID) -> Image:
        """L'image, verrouillée jusqu'à la fin de l'action : deux super admins qui agissent en
        même temps sur la même image ne déplacent pas son fichier deux fois."""
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
        """Écrit l'action au journal et valide le nouveau statut avec elle. Si la base échoue,
        la copie faite juste avant (copied_key) est retirée, et l'erreur remonte."""
        try:
            self._moderation_log.record(
                super_admin,
                action,
                ModerationTargetType.IMAGE,
                image.id,
                # Aucun nom de fichier n'est gardé : la clé est unique et se lit dans l'URL
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
        """Efface un fichier devenu inutile. Si le stockage échoue, la clé est journalisée pour un
        effacement à la main : la décision, déjà validée, reste."""
        try:
            self._storage.delete(key)
        except BotoCoreError, ClientError:
            logger.exception("Fichier d'image non effacé : storage_key=%s", key)
