import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants.templates import OFFICIAL_ACCOUNT_ID
from app.core.config import Settings
from app.exceptions.templates import (
    OfficialTemplateLockedError,
    TemplateHasNoTilesError,
    TemplateHiddenError,
    TemplateNotFoundError,
    TemplateNotPublishedError,
)
from app.models.enums import (
    ModerationActionKind,
    ModerationTargetType,
    TemplateModeration,
    TemplateVisibility,
)
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as template_repository
from app.services.moderation_log import ModerationLogService
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OfficialTemplateSummary:
    template: Template
    tile_count: int
    editor_name: str | None


class OfficialTemplateService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        templates: TemplateService,
        moderation_log: ModerationLogService,
    ) -> None:
        self._session = session
        self._settings = settings
        self._templates = templates
        self._moderation_log = moderation_log

    def list(self) -> list[OfficialTemplateSummary]:
        now: datetime = datetime.now(UTC)
        summaries: list[OfficialTemplateSummary] = []
        for template, tile_count in template_repository.list_official_templates_with_tile_count(
            self._session
        ):
            editor: User | None = template.active_editor(now)
            summaries.append(
                OfficialTemplateSummary(
                    template, tile_count, None if editor is None else editor.display_name
                )
            )
        return summaries

    def create(self, super_admin: User, name: str) -> Template:
        official_account: User | None = self._session.get(User, OFFICIAL_ACCOUNT_ID)
        if official_account is None:
            raise RuntimeError("The official account is created by the migration 7b2e4c9d1a03")
        template: Template = self._templates.add_new(official_account, name)
        self._take_lease(super_admin, template)
        self._record(super_admin, ModerationActionKind.CREATE, template)
        template.edit_logged = True
        self._session.commit()
        logger.info(
            "Modèle officiel créé : template_id=%s super_admin_id=%s", template.id, super_admin.id
        )
        return template

    def lock(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_update(template_id)
        editor: User | None = template.active_editor(datetime.now(UTC))
        if editor is not None and editor.id != super_admin.id:
            raise OfficialTemplateLockedError(editor.display_name)
        if editor is None:
            template.edit_logged = False
        self._take_lease(super_admin, template)
        self._session.commit()
        return template

    def unlock(self, super_admin: User, template_id: uuid.UUID) -> None:
        template: Template = self._get_for_update(template_id)
        if template.editing_by_id == super_admin.id:
            template.editing_by_id = None
            template.editing_until = None
        self._session.commit()

    def publish(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.visibility == TemplateVisibility.PUBLIC:
            return template
        if template.moderation == TemplateModeration.HIDDEN:
            raise TemplateHiddenError
        if not template.tiles:
            raise TemplateHasNoTilesError
        template.visibility = TemplateVisibility.PUBLIC
        if template.first_made_public_at is None:
            template.first_made_public_at = func.clock_timestamp()
        return self._commit_editorial_change(super_admin, ModerationActionKind.PUBLISH, template)

    def unpublish(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.visibility == TemplateVisibility.PRIVATE:
            return template
        template.visibility = TemplateVisibility.PRIVATE
        template.featured_at = None
        return self._commit_editorial_change(super_admin, ModerationActionKind.UNPUBLISH, template)

    def feature(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.featured_at is not None:
            return template
        if template.visibility != TemplateVisibility.PUBLIC:
            raise TemplateNotPublishedError
        template.featured_at = func.clock_timestamp()
        return self._commit_editorial_change(super_admin, ModerationActionKind.FEATURE, template)

    def unfeature(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.featured_at is None:
            return template
        template.featured_at = None
        return self._commit_editorial_change(super_admin, ModerationActionKind.UNFEATURE, template)

    def delete(self, super_admin: User, template_id: uuid.UUID) -> None:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        template.deleted_at = datetime.now(UTC)
        template.featured_at = None
        template.editing_by_id = None
        template.editing_until = None
        self._commit_editorial_change(super_admin, ModerationActionKind.DELETE, template)

    def _get_for_update(self, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_official_template(
            self._session, template_id, for_update=True
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def _get_for_editorial_change(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_update(template_id)
        editor: User | None = template.active_editor(datetime.now(UTC))
        if editor is not None and editor.id != super_admin.id:
            raise OfficialTemplateLockedError(editor.display_name)
        return template

    def _take_lease(self, super_admin: User, template: Template) -> None:
        template.editing_by_id = super_admin.id
        template.editing_by = super_admin
        template.editing_until = datetime.now(UTC) + self._settings.official_template_lock

    def _commit_editorial_change(
        self, super_admin: User, action: ModerationActionKind, template: Template
    ) -> Template:
        self._record(super_admin, action, template)
        self._session.commit()
        logger.info(
            "Modèle officiel %s : template_id=%s super_admin_id=%s",
            action,
            template.id,
            super_admin.id,
        )
        return template

    def _record(self, super_admin: User, action: ModerationActionKind, template: Template) -> None:
        self._moderation_log.record(
            super_admin,
            action,
            ModerationTargetType.TEMPLATE,
            template.id,
            template.name,
            reason=None,
        )
