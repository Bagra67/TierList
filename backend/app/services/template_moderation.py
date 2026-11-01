"""Modération des templates (US-1.5, docs/technical/templates.md) : masquer, réafficher ou
supprimer le template d'un utilisateur.

La modération est séparée de ce que choisit le propriétaire : un template masqué reste le sien, il
le voit et le modifie encore, mais aucune nouvelle salle ni nouvelle partie ne peut être lancée
avec. Les parties en cours continuent : elles ne dépendent que de leur version figée.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.exceptions.templates import TemplateModerationConflictError, TemplateNotFoundError
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateModeration
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as template_repository
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)


class TemplateModerationService:
    def __init__(self, session: Session, moderation_log: ModerationLogService) -> None:
        self._session = session
        self._moderation_log = moderation_log

    def hide(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        """Masque un template avec un motif, que son propriétaire verra. Lève
        TemplateNotFoundError ou TemplateModerationConflictError."""
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None or template.moderation == TemplateModeration.HIDDEN:
            raise TemplateModerationConflictError
        self._apply(
            super_admin,
            ModerationActionKind.HIDE,
            template,
            reason,
            {"moderation": TemplateModeration.HIDDEN, "moderation_reason": reason},
        )
        logger.info(
            "Template masqué : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def unhide(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        """Réaffiche un template masqué : il retrouve l'état que son propriétaire avait choisi.
        Lève TemplateNotFoundError ou TemplateModerationConflictError."""
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None or template.moderation != TemplateModeration.HIDDEN:
            raise TemplateModerationConflictError
        self._apply(
            super_admin,
            ModerationActionKind.UNHIDE,
            template,
            reason,
            {"moderation": TemplateModeration.NONE, "moderation_reason": None},
        )
        logger.info(
            "Template réaffiché : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def delete(self, super_admin: User, template_id: uuid.UUID, reason: str) -> None:
        """Supprime un template, masqué ou non, comme son propriétaire le ferait : suppression
        logique, puis purge ; les parties déjà jouées gardent leur version figée. Lève
        TemplateNotFoundError ou TemplateModerationConflictError."""
        template: Template = self._get_template(template_id)
        if template.deleted_at is not None:
            raise TemplateModerationConflictError
        self._apply(
            super_admin,
            ModerationActionKind.DELETE,
            template,
            reason,
            {"deleted_at": datetime.now(UTC)},
        )
        logger.info(
            "Template supprimé : template_id=%s super_admin_id=%s", template_id, super_admin.id
        )

    def _get_template(self, template_id: uuid.UUID) -> Template:
        """Le template, de n'importe quel propriétaire, verrouillé jusqu'à la fin de l'action.
        Un template purgé n'existe plus : introuvable."""
        template: Template | None = template_repository.get_template_for_update(
            self._session, template_id
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def _apply(
        self,
        super_admin: User,
        action: ModerationActionKind,
        template: Template,
        reason: str,
        changes: dict[str, Any],
    ) -> None:
        """Change le template et écrit l'action au journal, validés ensemble. updated_at reste
        tel quel : c'est la dernière modification du propriétaire, pas une décision de la
        modération."""
        self._session.execute(
            update(Template)
            .where(Template.id == template.id)
            .values(**changes, updated_at=Template.updated_at)
        )
        self._moderation_log.record(
            super_admin, action, ModerationTargetType.TEMPLATE, template.id, template.name, reason
        )
        self._session.commit()
