"""Règles métier des templates : création avec les tiers par défaut, liste, renommage,
configuration des tiers, suppression logique et purge définitive.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Un template n'est visible que de son propriétaire.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants.templates import DEFAULT_TIERS, NEW_TIER_COLOR, NEW_TIER_NAME
from app.core.config import Settings
from app.exceptions.templates import LastTierError, TemplateNotFoundError, TierNotFoundError
from app.models.template import Template
from app.models.tier import Tier
from app.models.user import User
from app.repositories import templates as template_repository

logger = logging.getLogger(__name__)


def _renumber(tiers: list[Tier]) -> None:
    """Positions continues 0..n-1 dans l'ordre de la liste (aucune contrainte d'unicité en base)."""
    for position, tier in enumerate(tiers):
        tier.position = position


def _move(tiers: list[Tier], tier: Tier, position: int) -> None:
    """Déplace le tier à cette position ; au-delà de la fin, il passe en dernier."""
    tiers.remove(tier)
    tiers.insert(min(position, len(tiers)), tier)
    _renumber(tiers)


@dataclass(frozen=True)
class TemplateSummary:
    """Un template dans la liste « Mes templates »."""

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


class TierChanges(TypedDict, total=False):
    """Modifications d'un tier : seules les clés présentes changent. Hors position, chaque clé
    est un attribut de Tier, recopié tel quel : un nouveau champ simple n'a besoin que d'une
    clé ici."""

    name: str
    color: str
    position: int


class TemplateService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def create(self, owner: User, name: str) -> Template:
        """Crée un template privé, avec les tiers par défaut et sans tuile."""
        template: Template = Template(
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
        """Templates actifs du propriétaire, le plus récemment modifié d'abord."""
        templates_with_tile_count: list[tuple[Template, int]] = (
            template_repository.list_owned_templates_with_tile_count(self._session, owner.id)
        )

        summaries: list[TemplateSummary] = []
        for template, tile_count in templates_with_tile_count:
            summary: TemplateSummary = TemplateSummary(
                id=template.id,
                name=template.name,
                tile_count=tile_count,
                updated_at=template.updated_at,
            )
            summaries.append(summary)
        return summaries

    def get(self, owner: User, template_id: uuid.UUID) -> Template:
        template: Template | None = template_repository.get_owned_template(
            self._session, template_id, owner.id
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def rename(self, owner: User, template_id: uuid.UUID, name: str) -> Template:
        template: Template = self.get(owner, template_id)
        template.name = name
        self._session.commit()
        return template

    def add_tier(self, owner: User, template_id: uuid.UUID) -> Template:
        """Ajoute un tier en bas, avec le nom et la couleur par défaut."""
        template: Template = self._get_for_change(owner, template_id)
        new_tier: Tier = Tier(
            name=NEW_TIER_NAME, color=NEW_TIER_COLOR, position=len(template.tiers)
        )
        template.tiers.append(new_tier)
        self._save_change(template)
        return template

    def update_tier(
        self,
        owner: User,
        template_id: uuid.UUID,
        tier_id: uuid.UUID,
        changes: TierChanges,
    ) -> Template:
        """Renomme, recolore et/ou déplace un tier ; les champs absents restent tels quels."""
        template: Template = self._get_for_change(owner, template_id)
        tier: Tier = self._get_tier(template, tier_id)
        if not changes:
            # Rien à modifier : la date de dernière modification ne bouge pas (le commit libère
            # seulement le verrou)
            self._session.commit()
            return template
        for field_name, value in changes.items():
            # La position ne se recopie pas : déplacer un tier décale aussi les autres
            if field_name != "position":
                setattr(tier, field_name, value)
        if "position" in changes:
            _move(template.tiers, tier, changes["position"])
        self._save_change(template)
        return template

    def delete_tier(self, owner: User, template_id: uuid.UUID, tier_id: uuid.UUID) -> Template:
        """Supprime un tier ; le dernier tier d'un template ne peut pas l'être."""
        template: Template = self._get_for_change(owner, template_id)
        tier: Tier = self._get_tier(template, tier_id)
        if len(template.tiers) == 1:
            raise LastTierError
        # delete-orphan : retiré de la liste, le tier est supprimé de la base
        template.tiers.remove(tier)
        _renumber(template.tiers)
        self._save_change(template)
        return template

    def _get_for_change(self, owner: User, template_id: uuid.UUID) -> Template:
        """Template à modifier, verrouillé jusqu'au commit : les règles « au moins un tier » et
        « au plus max_tiles tuiles » tiennent même avec des requêtes simultanées."""
        template: Template | None = template_repository.get_owned_template(
            self._session, template_id, owner.id, for_update=True
        )
        if template is None:
            raise TemplateNotFoundError
        return template

    def _save_change(self, template: Template) -> None:
        """Valide une modification des tiers ou des tuiles du template, en mettant à jour sa date
        de dernière modification : onupdate ne voit pas les changements des autres tables."""
        template.updated_at = func.clock_timestamp()
        self._session.commit()

    @staticmethod
    def _get_tier(template: Template, tier_id: uuid.UUID) -> Tier:
        for tier in template.tiers:
            if tier.id == tier_id:
                return tier
        raise TierNotFoundError

    def delete(self, owner: User, template_id: uuid.UUID) -> None:
        """Suppression logique : le template disparaît pour son propriétaire, et sera purgé
        définitivement après DELETED_TEMPLATE_RETENTION_DAYS (purge_deleted)."""
        template: Template = self.get(owner, template_id)
        template.deleted_at = datetime.now(UTC)
        self._session.commit()
        logger.info("Template supprimé : template_id=%s owner_id=%s", template.id, owner.id)

    def purge_deleted(self) -> int:
        """Supprime définitivement les templates supprimés depuis plus que la durée de
        rétention ; renvoie leur nombre."""
        limit: datetime = datetime.now(UTC) - timedelta(
            days=self._settings.deleted_template_retention_days
        )
        purged: int = template_repository.delete_templates_deleted_before(self._session, limit)
        self._session.commit()
        logger.info("Templates purgés : %d (supprimés avant %s)", purged, limit.isoformat())
        return purged
