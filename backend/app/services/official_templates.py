import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.constants.templates import OFFICIAL_ACCOUNT_ID
from app.core.config import Settings
from app.exceptions.templates import (
    OfficialTemplateLockedError,
    TemplateNotFoundError,
    TemplateNotPublishedError,
)
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateVisibility
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as template_repository
from app.repositories import users as user_repository
from app.services.moderation_log import ModerationLogService
from app.services.templates import TemplateService, check_publishable, mark_made_public

logger = logging.getLogger(__name__)


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

    def list(self) -> list[tuple[Template, int]]:
        return template_repository.list_owned_templates_with_tile_count(
            self._session, OFFICIAL_ACCOUNT_ID
        )

    def create(self, super_admin: User, name: str) -> Template:
        official_account: User = user_repository.get_official_account(self._session)
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
        template: Template = self._get_row_for_update(template_id)
        self._check_not_held_by_another(super_admin, template)
        if template.active_editor(datetime.now(UTC)) is None:
            template.edit_logged = False
        self._take_lease(super_admin, template)
        self._session.commit()
        return template

    def unlock(self, super_admin: User, template_id: uuid.UUID) -> None:
        template: Template = self._get_row_for_update(template_id)
        if template.editing_by_id == super_admin.id:
            template.editing_by_id = None
            template.editing_until = None
        self._session.commit()

    def publish(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.visibility == TemplateVisibility.PUBLIC:
            return template
        check_publishable(template)
        mark_made_public(template)
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
        template.featured_at = datetime.now(UTC)
        return self._commit_editorial_change(super_admin, ModerationActionKind.FEATURE, template)

    def unfeature(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template = self._get_for_editorial_change(super_admin, template_id)
        if template.featured_at is None:
            return template
        template.featured_at = None
        return self._commit_editorial_change(super_admin, ModerationActionKind.UNFEATURE, template)

    def delete(self, super_admin: User, template_id: uuid.UUID) -> None:
        template: Template = self._get_row_for_update(template_id)
        self._check_not_held_by_another(super_admin, template)
        template.deleted_at = datetime.now(UTC)
        template.featured_at = None
        template.editing_by_id = None
        template.editing_until = None
        self._commit_editorial_change(super_admin, ModerationActionKind.DELETE, template)

    def _get_row_for_update(self, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_template_for_update(
            self._session, template_id
        )
        if template is None or not template.is_official or template.deleted_at is not None:
            raise TemplateNotFoundError
        return template

    def _get_for_editorial_change(self, super_admin: User, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_owned_template(
            self._session, template_id, OFFICIAL_ACCOUNT_ID, for_update=True
        )
        if template is None:
            raise TemplateNotFoundError
        self._check_not_held_by_another(super_admin, template)
        return template

    @staticmethod
    def _check_not_held_by_another(super_admin: User, template: Template) -> None:
        editor: User | None = template.active_editor(datetime.now(UTC))
        if editor is not None and editor.id != super_admin.id:
            raise OfficialTemplateLockedError(editor.display_name)

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
