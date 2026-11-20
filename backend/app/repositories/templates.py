import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    ColumnElement,
    Select,
    and_,
    delete,
    exists,
    func,
    or_,
    select,
    text,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.dml import ReturningDelete

from app.constants.marketplace import MarketplaceSort
from app.constants.templates import OFFICIAL_ACCOUNT_ID
from app.models.account_ban import AccountBan
from app.models.enums import TemplateModeration, TemplateVisibility, UserRole
from app.models.image import Image, ImageStatus
from app.models.template import Template
from app.models.template_like import TemplateLike
from app.models.template_snapshot import TemplateSnapshot
from app.models.template_tag import TemplateTag
from app.models.tile import Tile
from app.models.user import User
from app.repositories.account_bans import is_active
from app.repositories.users import user_matches


class RowLock(StrEnum):
    UPDATE = "update"
    SHARE = "share"


def add_template(session: Session, template: Template) -> None:
    session.add(template)


def add_snapshot(session: Session, snapshot: TemplateSnapshot) -> None:
    session.add(snapshot)


def get_owned_template(
    session: Session, template_id: uuid.UUID, owner_id: uuid.UUID, for_update: bool = False
) -> Template | None:
    return _get_template_with_content(
        session,
        and_(
            Template.id == template_id,
            Template.owner_id == owner_id,
            Template.deleted_at.is_(None),
        ),
        RowLock.UPDATE if for_update else None,
    )


def get_editable_template(
    session: Session, template_id: uuid.UUID, user_id: uuid.UUID, for_update: bool = False
) -> Template | None:
    user_is_super_admin: ColumnElement[bool] = exists().where(
        User.id == user_id, User.role == UserRole.SUPER_ADMIN
    )
    return _get_template_with_content(
        session,
        and_(
            Template.id == template_id,
            or_(
                Template.owner_id == user_id,
                and_(Template.owner_id == OFFICIAL_ACCOUNT_ID, user_is_super_admin),
            ),
            Template.deleted_at.is_(None),
        ),
        RowLock.UPDATE if for_update else None,
    )


def get_playable_template(
    session: Session,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    now: datetime,
    for_share: bool = False,
) -> Template | None:
    return _get_template_with_content(
        session,
        and_(
            Template.id == template_id,
            Template.deleted_at.is_(None),
            or_(Template.owner_id == user_id, listed_templates_condition(now)),
        ),
        RowLock.SHARE if for_share else None,
    )


def _get_template_with_content(
    session: Session, condition: ColumnElement[bool], lock: RowLock | None
) -> Template | None:
    statement: Select[Template] = (
        select(Template)
        .where(condition)
        .options(
            selectinload(Template.tiers),
            selectinload(Template.tiles),
            selectinload(Template.tags),
        )
    )
    if lock is not None:
        statement = statement.with_for_update(read=lock == RowLock.SHARE, of=Template)
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


def _listed_templates_with_owner_name(now: datetime) -> Select[Template, str]:
    return (
        select(Template, User.display_name)
        .join(User, User.id == Template.owner_id)
        .where(listed_templates_condition(now))
        .options(selectinload(Template.tiers), selectinload(Template.tags))
    )


def get_listed_template_with_owner_name(
    session: Session, template_id: uuid.UUID, now: datetime
) -> tuple[Template, str] | None:
    statement: Select[Template, str] = (
        _listed_templates_with_owner_name(now)
        .where(Template.id == template_id)
        .options(selectinload(Template.tiles))
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


def list_listed_template_owner_ids(
    session: Session, template_ids: list[uuid.UUID], now: datetime
) -> dict[uuid.UUID, uuid.UUID]:
    statement: Select[uuid.UUID, uuid.UUID] = select(Template.id, Template.owner_id).where(
        Template.id.in_(template_ids), listed_templates_condition(now)
    )
    return {template_id: owner_id for template_id, owner_id in session.execute(statement)}


def get_template_for_review(session: Session, template_id: uuid.UUID) -> Template | None:
    statement: Select[Template] = (
        select(Template)
        .where(Template.id == template_id)
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
            **({"featured_at": None} if moderation == TemplateModeration.HIDDEN else {}),
        )
    )


def mark_template_deleted(
    session: Session, template_id: uuid.UUID, deleted_at: datetime, deletion_reason: str
) -> None:
    session.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(
            deleted_at=deleted_at,
            deletion_reason=deletion_reason,
            featured_at=None,
            updated_at=Template.updated_at,
        )
    )


def mark_template_restored(session: Session, template_id: uuid.UUID) -> None:
    session.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(deleted_at=None, deletion_reason=None, updated_at=Template.updated_at)
    )


def delete_template_permanently(session: Session, template_id: uuid.UUID) -> None:
    session.execute(delete(Template).where(Template.id == template_id))


def list_templates_deleted_by_moderation(session: Session, owner_id: uuid.UUID) -> list[Template]:
    statement: Select[Template] = (
        select(Template)
        .where(
            Template.owner_id == owner_id,
            Template.deleted_at.is_not(None),
            Template.deletion_reason.is_not(None),
        )
        .order_by(Template.deleted_at.desc(), Template.id)
    )
    return list(session.scalars(statement).all())


def list_deleted_templates(
    session: Session,
    owner_query: str | None,
    name_query: str | None,
    deleted_after: datetime | None,
    deleted_before: datetime | None,
    limit: int,
    offset: int,
) -> list[tuple[Template, str, int]]:
    tile_count: ColumnElement[int] = (
        select(func.count()).where(Tile.template_id == Template.id).scalar_subquery()
    )
    statement: Select[Template, str, int] = (
        select(Template, User.display_name, tile_count)
        .join(User, User.id == Template.owner_id)
        .where(Template.deleted_at.is_not(None))
    )
    if owner_query:
        statement = statement.where(user_matches(owner_query))
    if name_query:
        statement = statement.where(Template.name.icontains(name_query, autoescape=True))
    if deleted_after is not None:
        statement = statement.where(Template.deleted_at >= deleted_after)
    if deleted_before is not None:
        statement = statement.where(Template.deleted_at < deleted_before)
    statement = statement.order_by(Template.deleted_at, Template.id).limit(limit).offset(offset)
    return [
        (template, owner_name, count) for template, owner_name, count in session.execute(statement)
    ]


def list_owned_templates_with_tile_count(
    session: Session,
    owner_id: uuid.UUID,
    after: tuple[datetime, uuid.UUID] | None = None,
    limit: int | None = None,
) -> list[tuple[Template, int]]:
    statement: Select[Template, int] = (
        select(Template, func.count(Tile.id))
        .outerjoin(Tile, Tile.template_id == Template.id)
        .where(Template.owner_id == owner_id, Template.deleted_at.is_(None))
        .group_by(Template.id)
        .order_by(Template.updated_at.desc(), Template.id.desc())
        .limit(limit)
    )
    if after is not None:
        statement = statement.where(tuple_(Template.updated_at, Template.id) < tuple_(*after))
    return [(template, tile_count) for template, tile_count in session.execute(statement)]


def list_tags_of_templates(session: Session, template_ids: list[uuid.UUID]) -> list[TemplateTag]:
    statement: Select[TemplateTag] = (
        select(TemplateTag)
        .where(TemplateTag.template_id.in_(template_ids))
        .order_by(TemplateTag.position)
    )
    return list(session.scalars(statement).all())


def list_tiles_with_removed_image_of_templates(
    session: Session, template_ids: list[uuid.UUID]
) -> list[tuple[Tile, Image]]:
    statement: Select[Tile, Image] = (
        select(Tile, Image)
        .join(Image, Tile.image_id == Image.id)
        .where(Tile.template_id.in_(template_ids), Image.status != ImageStatus.VISIBLE)
        .order_by(Tile.position, Tile.id)
    )
    return [(tile, image) for tile, image in session.execute(statement)]


def delete_templates_deleted_before(session: Session, limit: datetime) -> int:
    statement: ReturningDelete[uuid.UUID] = (
        delete(Template).where(Template.deleted_at < limit).returning(Template.id)
    )
    return len(session.scalars(statement).all())


@dataclass(frozen=True)
class MarketplaceAfter:
    like_count: int | None
    first_made_public_at: datetime
    id: uuid.UUID


def list_marketplace_templates(
    session: Session,
    now: datetime,
    search_query: str | None,
    normalized_tag: str | None,
    sort: MarketplaceSort,
    after: MarketplaceAfter | None,
    limit: int,
) -> list[tuple[Template, str, int]]:
    like_counts = (
        select(TemplateLike.template_id, func.count().label("like_count"))
        .group_by(TemplateLike.template_id)
        .subquery()
    )
    like_count: ColumnElement[int] = func.coalesce(like_counts.c.like_count, 0)
    statement: Select[Template, str, int] = (
        _listed_templates_with_owner_name(now)
        .add_columns(like_count)
        .outerjoin(like_counts, like_counts.c.template_id == Template.id)
        .limit(limit)
    )
    if search_query is not None:
        statement = statement.where(
            func.to_tsvector(text("'simple'"), Template.search_text).op("@@")(
                func.to_tsquery(text("'simple'"), search_query)
            )
        )
    if normalized_tag is not None:
        statement = statement.where(
            exists().where(
                TemplateTag.template_id == Template.id,
                TemplateTag.normalized_label == normalized_tag,
            )
        )
    if sort == MarketplaceSort.POPULAR:
        statement = statement.order_by(
            like_count.desc(), Template.first_made_public_at.desc(), Template.id.desc()
        )
        if after is not None:
            statement = statement.where(
                tuple_(like_count, Template.first_made_public_at, Template.id)
                < tuple_(after.like_count, after.first_made_public_at, after.id)
            )
    else:
        statement = statement.order_by(Template.first_made_public_at.desc(), Template.id.desc())
        if after is not None:
            statement = statement.where(
                tuple_(Template.first_made_public_at, Template.id)
                < tuple_(after.first_made_public_at, after.id)
            )
    return [
        (template, owner_name, count) for template, owner_name, count in session.execute(statement)
    ]


def list_featured_templates(
    session: Session, now: datetime, limit: int
) -> list[tuple[Template, str, int]]:
    like_count: ColumnElement[int] = (
        select(func.count())
        .where(TemplateLike.template_id == Template.id)
        .correlate(Template)
        .scalar_subquery()
    )
    statement: Select[Template, str, int] = (
        _listed_templates_with_owner_name(now)
        .add_columns(like_count)
        .where(Template.featured_at.is_not(None))
        .order_by(Template.featured_at.desc(), Template.id.desc())
        .limit(limit)
    )
    return [
        (template, owner_name, count) for template, owner_name, count in session.execute(statement)
    ]


def list_popular_listed_tags(session: Session, now: datetime, limit: int) -> list[str]:
    statement: Select[str] = (
        select(func.min(TemplateTag.label))
        .join(Template, Template.id == TemplateTag.template_id)
        .where(listed_templates_condition(now))
        .group_by(TemplateTag.normalized_label)
        .order_by(func.count().desc(), TemplateTag.normalized_label)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def count_tiles_of_templates(
    session: Session, template_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    statement: Select[uuid.UUID, int] = (
        select(Tile.template_id, func.count())
        .where(Tile.template_id.in_(template_ids))
        .group_by(Tile.template_id)
    )
    return {template_id: count for template_id, count in session.execute(statement)}


def list_first_tiles_of_templates(
    session: Session, template_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Tile]:
    statement: Select[Tile] = (
        select(Tile)
        .where(Tile.template_id.in_(template_ids))
        .ext(distinct_on(Tile.template_id))
        .order_by(Tile.template_id, Tile.position)
    )
    return {tile.template_id: tile for tile in session.scalars(statement)}
