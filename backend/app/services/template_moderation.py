import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions.templates import TemplateModerationConflictError, TemplateNotFoundError
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateModeration
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as template_repository
from app.repositories import users as user_repository
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewedTemplate:
    template: Template
    owner_name: str | None


class TemplateModerationService:
    def __init__(self, session: Session, moderation_log: ModerationLogService) -> None:
        self._session = session
        self._moderation_log = moderation_log

    def review(self, template_id: uuid.UUID) -> ReviewedTemplate:
        template: Template | None = template_repository.get_template_for_review(
            self._session, template_id
        )
        if template is None:
            raise TemplateNotFoundError
        owner: User | None = user_repository.get_user_by_id(self._session, template.owner_id)
        return ReviewedTemplate(template, owner.display_name if owner is not None else None)

    def hide(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None or template.moderation == TemplateModeration.HIDDEN:
            raise TemplateModerationConflictError
        template_repository.set_template_moderation(
            self._session, template.id, TemplateModeration.HIDDEN, reason
        )
        self._record_and_commit(super_admin, ModerationActionKind.HIDE, template, reason)
        logger.info(
            "Template masqué : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def unhide(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None or template.moderation != TemplateModeration.HIDDEN:
            raise TemplateModerationConflictError
        template_repository.set_template_moderation(
            self._session, template.id, TemplateModeration.NONE, None
        )
        self._record_and_commit(super_admin, ModerationActionKind.UNHIDE, template, reason)
        logger.info(
            "Template réaffiché : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def delete(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None:
            raise TemplateModerationConflictError
        template_repository.mark_template_deleted(self._session, template.id, datetime.now(UTC))
        self._record_and_commit(super_admin, ModerationActionKind.DELETE, template, reason)
        logger.info(
            "Template supprimé : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def _get_template(self, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_template_for_update(
            self._session, template_id
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def _record_and_commit(
        self, super_admin: User, action: ModerationActionKind, template: Template, reason: str
    ) -> None:
        self._moderation_log.record(
            super_admin, action, ModerationTargetType.TEMPLATE, template.id, template.name, reason
        )
        self._session.commit()
