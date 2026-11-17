import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, Select, and_, delete, exists, func, select, update
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.dml import ReturningDelete

from app.models.account_ban import AccountBan
from app.models.enums import TemplateModeration, TemplateVisibility
from app.models.image import Image, ImageStatus
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.template_tag import TemplateTag
from app.models.tile import Tile
from app.models.user import User
from app.repositories.account_bans import is_active


def add_template(session: Session, template: Template) -> None:
    session.add(template)


def add_snapshot(session: Session, snapshot: TemplateSnapshot) -> None:
    session.add(snapshot)


def get_owned_template(
    session: Session, template_id: uuid.UUID, owner_id: uuid.UUID, for_update: bool = False
) -> Template | None:
    statement: Select[Template] = (
        select(Template)
        .where(
            Template.id == template_id,
            Template.owner_id == owner_id,
            Template.deleted_at.is_(None),
        )
        .options(
            selectinload(Template.tiers),
            selectinload(Template.tiles),
            selectinload(Template.tags),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=Template)
    return session.scalars(statement).one_or_none()


def listed_templates_condition(now: datetime) -> ColumnElement[bool]:
    owner_is_banned: ColumnElement[bool] = exists().where(
        AccountBan.user_id == Template.owner_id, is_active(now)
    )
    return and_(
        Template.visibility == TemplateVisibility.PUBLIC,
        Template.moderation == TemplateModeration.NONE,
        Template.deleted_at.is_(None),
        ~owner_is_banned,
    )


def get_listed_template_with_owner_name(
    session: Session, template_id: uuid.UUID, now: datetime
) -> tuple[Template, str] | None:
    statement: Select[Template, str] = (
        select(Template, User.display_name)
        .join(User, User.id == Template.owner_id)
        .where(Template.id == template_id, listed_templates_condition(now))
        .options(
            selectinload(Template.tiers),
            selectinload(Template.tiles),
            selectinload(Template.tags),
        )
    )
    row = session.execute(statement).one_or_none()
    return None if row is None else (row[0], row[1])


def list_listed_template_updates(
    session: Session, now: datetime, limit: int
) -> list[tuple[uuid.UUID, datetime]]:
    statement: Select[uuid.UUID, datetime] = (
        select(Template.id, Template.updated_at)
        .where(listed_templates_condition(now))
        .order_by(Template.first_made_public_at.desc(), Template.id)
        .limit(limit)
    )
    return [(template_id, updated_at) for template_id, updated_at in session.execute(statement)]


def get_listed_template_name_and_owner(
    session: Session, template_id: uuid.UUID, now: datetime
) -> tuple[str, uuid.UUID] | None:
    statement: Select[str, uuid.UUID] = select(Template.name, Template.owner_id).where(
        Template.id == template_id, listed_templates_condition(now)
    )
    row = session.execute(statement).one_or_none()
    return None if row is None else (row[0], row[1])


def get_template_for_review(session: Session, template_id: uuid.UUID) -> Template | None:
    statement: Select[Template] = (
        select(Template)
        .where(Template.id == template_id, Template.deleted_at.is_(None))
        .options(selectinload(Template.tiers), selectinload(Template.tiles))
    )
    return session.scalars(statement).one_or_none()


def get_template_for_update(session: Session, template_id: uuid.UUID) -> Template | None:
    return session.get(Template, template_id, with_for_update=True)


def set_template_moderation(
    session: Session,
    template_id: uuid.UUID,
    moderation: TemplateModeration,
    moderation_reason: str | None,
) -> None:
    session.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(
            moderation=moderation,
            moderation_reason=moderation_reason,
            updated_at=Template.updated_at,
        )
    )


def mark_template_deleted(session: Session, template_id: uuid.UUID, deleted_at: datetime) -> None:
    session.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(deleted_at=deleted_at, updated_at=Template.updated_at)
    )


def list_owned_templates_with_tile_count(
    session: Session, owner_id: uuid.UUID
) -> list[tuple[Template, int]]:
    statement: Select[Template, int] = (
        select(Template, func.count(Tile.id))
        .outerjoin(Tile, Tile.template_id == Template.id)
        .where(Template.owner_id == owner_id, Template.deleted_at.is_(None))
        .group_by(Template.id)
        .order_by(Template.updated_at.desc(), Template.id)
    )
    return [(template, tile_count) for template, tile_count in session.execute(statement)]


def list_tags_of_owner(session: Session, owner_id: uuid.UUID) -> list[TemplateTag]:
    statement: Select[TemplateTag] = (
        select(TemplateTag)
        .join(Template, TemplateTag.template_id == Template.id)
        .where(Template.owner_id == owner_id, Template.deleted_at.is_(None))
        .order_by(TemplateTag.position)
    )
    return list(session.scalars(statement).all())


def list_tiles_with_removed_image_of_owner(
    session: Session, owner_id: uuid.UUID
) -> list[tuple[Tile, Image]]:
    statement: Select[Tile, Image] = (
        select(Tile, Image)
        .join(Image, Tile.image_id == Image.id)
        .join(Template, Tile.template_id == Template.id)
        .where(
            Template.owner_id == owner_id,
            Template.deleted_at.is_(None),
            Image.status != ImageStatus.VISIBLE,
        )
        .order_by(Tile.position, Tile.id)
    )
    return [(tile, image) for tile, image in session.execute(statement)]


def delete_templates_deleted_before(session: Session, limit: datetime) -> int:
    statement: ReturningDelete[uuid.UUID] = (
        delete(Template).where(Template.deleted_at < limit).returning(Template.id)
    )
    return len(session.scalars(statement).all())
