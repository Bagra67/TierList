"""Règles métier des templates : création avec les tiers par défaut, liste, renommage,
suppression logique et purge définitive.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Un template n'est visible que de son propriétaire.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.constants.templates import DEFAULT_TIERS
from app.core.config import Settings
from app.exceptions.templates import TemplateNotFoundError
from app.models.template import Template
from app.models.tier import Tier
from app.models.user import User
from app.repositories import templates as template_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TemplateSummary:
    """Un template dans la liste « Mes templates »."""

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


class TemplateService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def create(self, owner: User, name: str) -> Template:
        """Crée un template privé, avec les tiers par défaut et sans tuile."""
        template = Template(
            owner_id=owner.id,
            name=name,
            tiers=[
                Tier(name=tier_name, color=color, position=position)
                for position, (tier_name, color) in enumerate(DEFAULT_TIERS)
            ],
        )
        template_repository.add_template(self._session, template)
        self._session.commit()
        logger.info("Template créé : template_id=%s owner_id=%s", template.id, owner.id)
        return template

    def list_for_owner(self, owner: User) -> list[TemplateSummary]:
        return [
            TemplateSummary(
                id=template.id,
                name=template.name,
                tile_count=tile_count,
                updated_at=template.updated_at,
            )
            for template, tile_count in template_repository.list_owned_templates_with_tile_count(
                self._session, owner.id
            )
        ]

    def get(self, owner: User, template_id: uuid.UUID) -> Template:
        template = template_repository.get_owned_template(self._session, template_id, owner.id)
        if template is None:
            raise TemplateNotFoundError
        return template

    def rename(self, owner: User, template_id: uuid.UUID, name: str) -> Template:
        template = self.get(owner, template_id)
        template.name = name
        self._session.commit()
        return template

    def delete(self, owner: User, template_id: uuid.UUID) -> None:
        """Suppression logique : le template disparaît pour son propriétaire, et sera purgé
        définitivement après DELETED_TEMPLATE_RETENTION_DAYS (purge_deleted)."""
        template = self.get(owner, template_id)
        template.deleted_at = datetime.now(UTC)
        self._session.commit()
        logger.info("Template supprimé : template_id=%s owner_id=%s", template.id, owner.id)

    def purge_deleted(self, now: datetime) -> int:
        """Supprime définitivement les templates supprimés depuis plus que la durée de
        rétention ; renvoie leur nombre."""
        limit = now - timedelta(days=self._settings.deleted_template_retention_days)
        purged = template_repository.delete_templates_deleted_before(self._session, limit)
        self._session.commit()
        logger.info("Templates purgés : %d (supprimés avant %s)", purged, limit.isoformat())
        return purged
