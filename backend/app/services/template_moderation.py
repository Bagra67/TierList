import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions.templates import TemplateModerationConflictError, TemplateNotFoundError
from app.models.enums import (
    ModerationActionKind,
    ModerationTargetType,
    ReportStatus,
    TemplateModeration,
)
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.user import User
from app.repositories import moderation_actions as moderation_action_repository
from app.repositories import reports as report_repository
from app.repositories import templates as template_repository
from app.repositories import users as user_repository
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)

ACTIONS_THAT_KEEP_REPORTS_OPEN: frozenset[ModerationActionKind] = frozenset(
    {ModerationActionKind.UNHIDE, ModerationActionKind.RESTORE}
)


@dataclass(frozen=True)
class TemplateDeletion:
    erase_at: datetime
    reason: str | None


@dataclass(frozen=True)
class ReviewedTemplate:
    template: Template
    owner_name: str | None
    deletion: TemplateDeletion | None


@dataclass(frozen=True)
class DeletedTemplate:
    template: Template
    owner_name: str
    tile_count: int
    deletion: TemplateDeletion


@dataclass(frozen=True)
class DeletedTemplatesPage:
    templates: list[DeletedTemplate]
    has_more: bool


class TemplateModerationService:
    def __init__(
        self, session: Session, moderation_log: ModerationLogService, settings: Settings
    ) -> None:
        self._session = session
        self._moderation_log = moderation_log
        self._retention: timedelta = timedelta(days=settings.deleted_template_retention_days)

    def review(self, template_id: uuid.UUID) -> ReviewedTemplate:
        template: Template | None = template_repository.get_template_for_review(
            self._session, template_id
        )
        if template is None:
            raise TemplateNotFoundError
        owner: User | None = user_repository.get_user_by_id(self._session, template.owner_id)
        deletion: TemplateDeletion | None = None
        if template.deleted_at is not None:
            deletion = TemplateDeletion(
                self._erase_at(template),
                moderation_action_repository.get_template_deletion_reason(
                    self._session, template.id
                ),
            )
        return ReviewedTemplate(
            template, owner.display_name if owner is not None else None, deletion
        )

    def list_deleted(
        self,
        limit: int,
        offset: int,
        owner_query: str | None,
        name_query: str | None,
        deleted_after: datetime | None,
        deleted_before: datetime | None,
    ) -> DeletedTemplatesPage:
        rows: list[moderation_action_repository.DeletedTemplateRow] = (
            moderation_action_repository.list_deleted_templates(
                self._session,
                owner_query,
                name_query,
                deleted_after,
                deleted_before,
                limit + 1,
                offset,
            )
        )
        templates: list[DeletedTemplate] = [
            DeletedTemplate(
                row.template,
                row.owner_name,
                row.tile_count,
                TemplateDeletion(self._erase_at(row.template), row.deletion_reason),
            )
            for row in rows[:limit]
        ]
        return DeletedTemplatesPage(templates=templates, has_more=len(rows) > limit)

    def hide(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None or template.moderation == TemplateModeration.HIDDEN:
            raise TemplateModerationConflictError
        template_repository.set_template_moderation(
            self._session, template.id, TemplateModeration.HIDDEN, reason
        )
        self._record(super_admin, ModerationActionKind.HIDE, template, reason)
        self._session.commit()
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
        self._record(super_admin, ModerationActionKind.UNHIDE, template, reason)
        self._session.commit()
        logger.info(
            "Template réaffiché : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def delete(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None:
            raise TemplateModerationConflictError
        template_repository.mark_template_deleted(self._session, template.id, datetime.now(UTC))
        self._record(super_admin, ModerationActionKind.DELETE, template, reason)
        self._session.commit()
        logger.info(
            "Template supprimé : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def restore(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_deleted_template(template_id)
        template_repository.mark_template_restored(self._session, template.id)
        self._record(super_admin, ModerationActionKind.RESTORE, template, reason)
        self._session.commit()
        logger.info(
            "Template restauré : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def purge(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        template: Template = self._get_deleted_template(template_id)
        self._record(super_admin, ModerationActionKind.PURGE, template, reason)
        template_repository.delete_template_permanently(self._session, template.id)
        self._session.commit()
        logger.info(
            "Template effacé définitivement : template_id=%s super_admin_id=%s",
            template_id,
            super_admin.id,
        )

    def _get_deleted_template(self, template_id: uuid.UUID) -> Template:
        template: Template = self._get_template(template_id)
        if template.deleted_at is None:
            raise TemplateModerationConflictError
        return template

    def _erase_at(self, template: Template) -> datetime:
        if template.deleted_at is None:
            raise RuntimeError("A deleted template has a deletion date")
        return template.deleted_at + self._retention

    def _get_template(self, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_template_for_update(
            self._session, template_id
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def _record(
        self, super_admin: User, action: ModerationActionKind, template: Template, reason: str
    ) -> None:
        moderation_action: ModerationAction = self._moderation_log.record(
            super_admin, action, ModerationTargetType.TEMPLATE, template.id, template.name, reason
        )
        if action not in ACTIONS_THAT_KEEP_REPORTS_OPEN:
            report_repository.close_open_reports(
                self._session,
                ModerationTargetType.TEMPLATE,
                [template.id],
                ReportStatus.ACTIONED,
                moderation_action.id,
            )
