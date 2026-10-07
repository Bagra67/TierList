import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.template import Template
from app.models.tile import Tile


def add_template(session: Session, template: Template) -> None:
    session.add(template)


def get_owned_template(
    session: Session, template_id: uuid.UUID, owner_id: uuid.UUID
) -> Template | None:
    """Template actif (non supprimé) du propriétaire, avec ses tiers et ses tuiles."""
    statement = (
        select(Template)
        .where(
            Template.id == template_id,
            Template.owner_id == owner_id,
            Template.deleted_at.is_(None),
        )
        .options(selectinload(Template.tiers), selectinload(Template.tiles))
    )
    return session.scalars(statement).one_or_none()


def list_owned_templates_with_tile_count(
    session: Session, owner_id: uuid.UUID
) -> list[tuple[Template, int]]:
    """Templates actifs du propriétaire et leur nombre de tuiles, le plus récemment modifié
    d'abord. Une seule requête : le nombre de tuiles est compté par la base (pas de N+1)."""
    statement = (
        select(Template, func.count(Tile.id))
        .outerjoin(Tile, Tile.template_id == Template.id)
        .where(Template.owner_id == owner_id, Template.deleted_at.is_(None))
        .group_by(Template.id)
        # id départage deux templates modifiés au même instant : l'ordre reste stable
        .order_by(Template.updated_at.desc(), Template.id)
    )
    return [(template, tile_count) for template, tile_count in session.execute(statement)]


def delete_templates_deleted_before(session: Session, limit: datetime) -> int:
    """Supprime définitivement les templates supprimés logiquement avant limit ; leurs tiers et
    tuiles partent avec eux (ON DELETE CASCADE). Renvoie le nombre de templates supprimés."""
    statement = delete(Template).where(Template.deleted_at < limit).returning(Template.id)
    return len(session.scalars(statement).all())
