"""Comptes vus par les super admins (US-1.8, docs/technical/moderation.md) : chercher un compte,
lire sa page, masquer toutes ses images."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.exceptions.auth import UserNotFoundError
from app.exceptions.images import ImageModerationConflictError
from app.models.user import User
from app.repositories import images as image_repository
from app.repositories import users as user_repository
from app.services.image_moderation import ImageModerationService
from app.services.templates import TemplateService, TemplateSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountSearchPage:
    # Par nom
    accounts: list[User]
    # Il reste des comptes après cette page
    has_more: bool


@dataclass(frozen=True)
class AccountDetails:
    user: User
    # Ses templates actifs, avec leur état de modération
    templates: list[TemplateSummary]


class AccountReviewService:
    def __init__(
        self,
        session: Session,
        templates: TemplateService,
        image_moderation: ImageModerationService,
    ) -> None:
        self._session = session
        self._templates = templates
        self._image_moderation = image_moderation

    def search(self, query: str | None, limit: int, offset: int) -> AccountSearchPage:
        """Les comptes dont le nom ou l'e-mail contient query, à partir de offset. Un compte de
        plus est lu pour savoir s'il en reste."""
        accounts: list[User] = user_repository.search_users(self._session, query, limit + 1, offset)
        return AccountSearchPage(accounts=accounts[:limit], has_more=len(accounts) > limit)

    def details(self, user_id: uuid.UUID) -> AccountDetails:
        """Le compte et ses templates. Lève UserNotFoundError."""
        user: User = self._get_user(user_id)
        return AccountDetails(user=user, templates=self._templates.list_for_owner(user))

    def hide_all_images(self, super_admin: User, user_id: uuid.UUID, reason: str) -> int:
        """Masque chaque image visible du compte, comme une à une (US-1.4) : son fichier passe en
        quarantaine et chacune a son entrée au journal. Renvoie le nombre d'images masquées.
        Chaque image est validée à part : après un échec, relancer reprend les images restées
        visibles. Lève UserNotFoundError."""
        self._get_user(user_id)
        image_ids: list[uuid.UUID] = image_repository.list_visible_image_ids_of_owner(
            self._session, user_id
        )
        hidden_count: int = 0
        for image_id in image_ids:
            try:
                self._image_moderation.hide(super_admin, image_id, reason)
            except ImageModerationConflictError:
                # Masquée ou supprimée entre-temps par un autre super admin : rien à faire
                continue
            hidden_count += 1
        logger.info(
            "Images d'un compte masquées : user_id=%s hidden_count=%d super_admin_id=%s",
            user_id,
            hidden_count,
            super_admin.id,
        )
        return hidden_count

    def _get_user(self, user_id: uuid.UUID) -> User:
        user: User | None = user_repository.get_user_by_id(self._session, user_id)
        if user is None:
            raise UserNotFoundError
        return user
