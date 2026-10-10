"""Règles métier des templates : création avec les tiers par défaut, liste, renommage,
configuration des tiers, tuiles, suppression logique et purge définitive.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Un template n'est visible que de son propriétaire.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants.templates import DEFAULT_TIERS, NEW_TIER_COLOR, NEW_TIER_NAME
from app.core.config import Settings
from app.exceptions.images import ImageNotFoundError
from app.exceptions.templates import (
    LastTierError,
    TemplateNotFoundError,
    TierNotFoundError,
    TileEmptyError,
    TileLimitReachedError,
    TileNotFoundError,
)
from app.models.image import Image
from app.models.template import Template
from app.models.tier import Tier
from app.models.tile import Tile
from app.models.user import User
from app.repositories import images as image_repository
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


class TileChanges(TypedDict, total=False):
    """Modifications d'une tuile : seules les clés présentes changent. Hors position, chaque clé
    est un attribut de Tile, recopié tel quel, comme pour TierChanges ; None retire le texte ou
    l'image."""

    text: str | None
    image_id: uuid.UUID | None
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

    def add_tile(
        self,
        owner: User,
        template_id: uuid.UUID,
        text: str | None,
        image_id: uuid.UUID | None,
    ) -> Template:
        """Ajoute une tuile à la fin, avec un texte, une image de l'utilisateur, ou les deux ;
        refusé au-delà du nombre maximal de tuiles."""
        if text is None and image_id is None:
            raise TileEmptyError
        template: Template = self._get_for_change(owner, template_id)
        if len(template.tiles) >= template.max_tiles:
            raise TileLimitReachedError(template.max_tiles)
        if image_id is not None:
            self._check_owned_image(owner, image_id)
        new_tile: Tile = Tile(text=text, image_id=image_id, position=len(template.tiles))
        template.tiles.append(new_tile)
        self._save_change(template)
        return template

    def update_tile(
        self,
        owner: User,
        template_id: uuid.UUID,
        tile_id: uuid.UUID,
        changes: TileChanges,
    ) -> Template:
        """Change le texte, l'image et/ou la place d'une tuile dans l'ordre du template ; la
        tuile doit garder un texte ou une image."""
        template: Template = self._get_for_change(owner, template_id)
        tile: Tile = self._get_tile(template, tile_id)
        if not changes:
            # Rien à modifier : la date de dernière modification ne bouge pas (le commit libère
            # seulement le verrou)
            self._session.commit()
            return template
        new_text: str | None = changes.get("text", tile.text)
        new_image_id: uuid.UUID | None = changes.get("image_id", tile.image_id)
        if new_text is None and new_image_id is None:
            raise TileEmptyError
        if "image_id" in changes and new_image_id is not None:
            self._check_owned_image(owner, new_image_id)
        for field_name, value in changes.items():
            # La position ne se recopie pas : déplacer une tuile décale aussi les autres
            if field_name != "position":
                setattr(tile, field_name, value)
        if "position" in changes:
            _move(template.tiles, tile, changes["position"])
        self._save_change(template)
        return template

    def delete_tile(self, owner: User, template_id: uuid.UUID, tile_id: uuid.UUID) -> Template:
        template: Template = self._get_for_change(owner, template_id)
        tile: Tile = self._get_tile(template, tile_id)
        # delete-orphan : retirée de la liste, la tuile est supprimée de la base
        template.tiles.remove(tile)
        _renumber(template.tiles)
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

    def _check_owned_image(self, owner: User, image_id: uuid.UUID) -> None:
        """Une tuile ne peut afficher qu'une image envoyée par le propriétaire du template."""
        image: Image | None = image_repository.get_owned_image(self._session, image_id, owner.id)
        if image is None:
            raise ImageNotFoundError

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
