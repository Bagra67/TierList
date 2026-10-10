"""Règles métier des templates : création avec les tiers par défaut, liste, renommage,
configuration des tiers, tuiles, suppression logique et purge définitive.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Un template n'est visible que de son propriétaire.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants.templates import DEFAULT_TIERS, NEW_TIER_COLOR, NEW_TIER_NAME
from app.core.config import Settings
from app.exceptions.templates import (
    LastTierError,
    TemplateNotFoundError,
    TierNotFoundError,
    TileLimitReachedError,
    TileNotFoundError,
)
from app.models.template import Template
from app.models.tier import Tier
from app.models.tile import Tile
from app.models.user import User
from app.repositories import templates as template_repository

logger = logging.getLogger(__name__)


# Les tiers et les tuiles sont ordonnés de la même façon, par leur position
Positioned = TypeVar("Positioned", Tier, Tile)


def _renumber(items: list[Positioned]) -> None:
    """Positions continues 0..n-1 dans l'ordre de la liste (aucune contrainte d'unicité en base)."""
    for position, item in enumerate(items):
        item.position = position


def _move(items: list[Positioned], item: Positioned, position: int) -> None:
    """Déplace l'élément à cette position ; au-delà de la fin, il passe en dernier."""
    items.remove(item)
    items.insert(min(position, len(items)), item)
    _renumber(items)


def _touch(template: Template) -> None:
    """Met à jour la dernière modification du template : onupdate ne voit pas les changements
    de ses tiers et de ses tuiles, qui sont dans d'autres tables."""
    template.updated_at = func.clock_timestamp()


@dataclass(frozen=True)
class TemplateSummary:
    """Un template dans la liste « Mes templates »."""

    id: uuid.UUID
    name: str
    tile_count: int
    updated_at: datetime


@dataclass(frozen=True)
class TierChanges:
    """Modifications d'un tier ; None = inchangé."""

    name: str | None = None
    color: str | None = None
    position: int | None = None


@dataclass(frozen=True)
class TileChanges:
    """Modifications d'une tuile ; None = inchangé."""

    text: str | None = None
    position: int | None = None


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
        """Templates actifs du propriétaire, le plus récemment modifié d'abord."""
        templates_with_tile_count: list[tuple[Template, int]] = (
            template_repository.list_owned_templates_with_tile_count(self._session, owner.id)
        )

        summaries: list[TemplateSummary] = []
        for template, tile_count in templates_with_tile_count:
            summary = TemplateSummary(
                id=template.id,
                name=template.name,
                tile_count=tile_count,
                updated_at=template.updated_at,
            )
            summaries.append(summary)
        return summaries

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

    def add_tier(self, owner: User, template_id: uuid.UUID) -> Template:
        """Ajoute un tier en bas, avec le nom et la couleur par défaut."""
        template = self.get(owner, template_id)
        template.tiers.append(
            Tier(name=NEW_TIER_NAME, color=NEW_TIER_COLOR, position=len(template.tiers))
        )
        _touch(template)
        self._session.commit()
        return template

    def update_tier(
        self,
        owner: User,
        template_id: uuid.UUID,
        tier_id: uuid.UUID,
        changes: TierChanges,
    ) -> Template:
        """Renomme, recolore et/ou déplace un tier ; les champs à None restent tels quels."""
        template = self.get(owner, template_id)
        tier = self._get_tier(template, tier_id)
        if changes.name is not None:
            tier.name = changes.name
        if changes.color is not None:
            tier.color = changes.color
        if changes.position is not None:
            _move(template.tiers, tier, changes.position)
        _touch(template)
        self._session.commit()
        return template

    def delete_tier(self, owner: User, template_id: uuid.UUID, tier_id: uuid.UUID) -> Template:
        """Supprime un tier ; le dernier tier d'un template ne peut pas l'être."""
        template = self.get(owner, template_id)
        tier = self._get_tier(template, tier_id)
        if len(template.tiers) == 1:
            raise LastTierError
        # delete-orphan : retiré de la liste, le tier est supprimé de la base
        template.tiers.remove(tier)
        _renumber(template.tiers)
        _touch(template)
        self._session.commit()
        return template

    def add_tile(self, owner: User, template_id: uuid.UUID, text: str) -> Template:
        """Ajoute une tuile texte à la fin ; refusé au-delà du nombre maximal de tuiles."""
        template = self.get(owner, template_id)
        if len(template.tiles) >= template.max_tiles:
            raise TileLimitReachedError(template.max_tiles)
        template.tiles.append(Tile(text=text, position=len(template.tiles)))
        _touch(template)
        self._session.commit()
        return template

    def update_tile(
        self,
        owner: User,
        template_id: uuid.UUID,
        tile_id: uuid.UUID,
        changes: TileChanges,
    ) -> Template:
        """Change le texte et/ou la place d'une tuile dans l'ordre du template."""
        template = self.get(owner, template_id)
        tile = self._get_tile(template, tile_id)
        if changes.text is not None:
            tile.text = changes.text
        if changes.position is not None:
            _move(template.tiles, tile, changes.position)
        _touch(template)
        self._session.commit()
        return template

    def delete_tile(self, owner: User, template_id: uuid.UUID, tile_id: uuid.UUID) -> Template:
        template = self.get(owner, template_id)
        tile = self._get_tile(template, tile_id)
        # delete-orphan : retirée de la liste, la tuile est supprimée de la base
        template.tiles.remove(tile)
        _renumber(template.tiles)
        _touch(template)
        self._session.commit()
        return template

    @staticmethod
    def _get_tile(template: Template, tile_id: uuid.UUID) -> Tile:
        for tile in template.tiles:
            if tile.id == tile_id:
                return tile
        raise TileNotFoundError

    @staticmethod
    def _get_tier(template: Template, tier_id: uuid.UUID) -> Tier:
        for tier in template.tiers:
            if tier.id == tier_id:
                return tier
        raise TierNotFoundError

    def delete(self, owner: User, template_id: uuid.UUID) -> None:
        """Suppression logique : le template disparaît pour son propriétaire, et sera purgé
        définitivement après DELETED_TEMPLATE_RETENTION_DAYS (purge_deleted)."""
        template = self.get(owner, template_id)
        template.deleted_at = datetime.now(UTC)
        self._session.commit()
        logger.info("Template supprimé : template_id=%s owner_id=%s", template.id, owner.id)

    def purge_deleted(self) -> int:
        """Supprime définitivement les templates supprimés depuis plus que la durée de
        rétention ; renvoie leur nombre."""
        limit = datetime.now(UTC) - timedelta(days=self._settings.deleted_template_retention_days)
        purged = template_repository.delete_templates_deleted_before(self._session, limit)
        self._session.commit()
        logger.info("Templates purgés : %d (supprimés avant %s)", purged, limit.isoformat())
        return purged
