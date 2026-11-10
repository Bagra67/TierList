import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants.moderation import HIDE_ALL_IMAGES_BATCH_SIZE
from app.exceptions.auth import UserNotFoundError
from app.exceptions.images import ImageModerationConflictError, ImageNotFoundError
from app.models.user import User
from app.repositories import images as image_repository
from app.repositories import users as user_repository
from app.services.image_moderation import ImageModerationService
from app.services.templates import TemplateService, TemplateSummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountSearchPage:
    accounts: list[User]
    has_more: bool


@dataclass(frozen=True)
class HiddenImagesBatch:
    hidden_count: int
    has_more: bool


@dataclass(frozen=True)
class AccountDetails:
    user: User
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
        accounts: list[User] = user_repository.search_users(self._session, query, limit + 1, offset)
        return AccountSearchPage(accounts=accounts[:limit], has_more=len(accounts) > limit)

    def details(self, user_id: uuid.UUID) -> AccountDetails:
        user: User = self._get_user(user_id)
        return AccountDetails(user=user, templates=self._templates.list_for_owner(user))

    def hide_all_images(
        self, super_admin: User, user_id: uuid.UUID, reason: str
    ) -> HiddenImagesBatch:
        self._get_user(user_id)
        image_ids: list[uuid.UUID] = image_repository.list_visible_image_ids_of_owner(
            self._session, user_id, HIDE_ALL_IMAGES_BATCH_SIZE + 1
        )
        hidden_count: int = 0
        for image_id in image_ids[:HIDE_ALL_IMAGES_BATCH_SIZE]:
            try:
                self._image_moderation.hide(super_admin, image_id, reason)
            except ImageModerationConflictError, ImageNotFoundError:
                continue
            hidden_count += 1
        logger.info(
            "Images d'un compte masquées : user_id=%s hidden_count=%d super_admin_id=%s",
            user_id,
            hidden_count,
            super_admin.id,
        )
        more_visible: bool = len(image_ids) > HIDE_ALL_IMAGES_BATCH_SIZE
        return HiddenImagesBatch(
            hidden_count=hidden_count, has_more=more_visible and hidden_count > 0
        )

    def _get_user(self, user_id: uuid.UUID) -> User:
        user: User | None = user_repository.get_user_by_id(self._session, user_id)
        if user is None:
            raise UserNotFoundError
        return user
