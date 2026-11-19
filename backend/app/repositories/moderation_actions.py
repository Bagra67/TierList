import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Select, Subquery, delete, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.dml import ReturningDelete

from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User


def add_moderation_action(session: Session, moderation_action: ModerationAction) -> None:
    session.add(moderation_action)


def delete_moderation_actions_before(session: Session, limit: datetime) -> int:
    statement: ReturningDelete[uuid.UUID] = (
        delete(ModerationAction)
        .where(ModerationAction.created_at < limit)
        .returning(ModerationAction.id)
    )
    return len(session.scalars(statement).all())


def _latest_deletion_actions() -> Subquery:
    return (
        select(ModerationAction)
        .where(
            ModerationAction.target_type == ModerationTargetType.TEMPLATE,
            ModerationAction.action.in_(
                [ModerationActionKind.DELETE, ModerationActionKind.RESTORE]
            ),
        )
        .ext(distinct_on(ModerationAction.target_id))
        .order_by(
            ModerationAction.target_id,
            ModerationAction.created_at.desc(),
            ModerationAction.id.desc(),
        )
        .subquery()
    )


def list_templates_deleted_by_moderation(
    session: Session, owner_id: uuid.UUID
) -> list[tuple[Template, ModerationAction]]:
    latest_action = aliased(ModerationAction, _latest_deletion_actions())
    statement: Select[Template, ModerationAction] = (
        select(Template, latest_action)
        .join(latest_action, latest_action.target_id == Template.id)
        .where(
            Template.owner_id == owner_id,
            Template.deleted_at.is_not(None),
            latest_action.action == ModerationActionKind.DELETE,
        )
        .order_by(latest_action.created_at.desc(), latest_action.id)
    )
    return [(template, action) for template, action in session.execute(statement)]


def get_template_deletion_reason(session: Session, template_id: uuid.UUID) -> str | None:
    latest_action = aliased(ModerationAction, _latest_deletion_actions())
    statement: Select[str] = select(latest_action.reason).where(
        latest_action.target_id == template_id,
        latest_action.action == ModerationActionKind.DELETE,
    )
    return session.scalars(statement).one_or_none()


@dataclass(frozen=True)
class DeletedTemplateRow:
    template: Template
    owner_name: str
    tile_count: int
    deletion_reason: str | None


def list_deleted_templates(
    session: Session,
    owner_query: str | None,
    name_query: str | None,
    deleted_after: datetime | None,
    deleted_before: datetime | None,
    limit: int,
    offset: int,
) -> list[DeletedTemplateRow]:
    latest_action = aliased(ModerationAction, _latest_deletion_actions())
    tile_count: ColumnElement[int] = (
        select(func.count()).where(Tile.template_id == Template.id).scalar_subquery()
    )
    statement: Select[Template, str, int, str, ModerationActionKind] = (
        select(Template, User.display_name, tile_count, latest_action.reason, latest_action.action)
        .join(User, User.id == Template.owner_id)
        .outerjoin(latest_action, latest_action.target_id == Template.id)
        .where(Template.deleted_at.is_not(None))
    )
    if owner_query:
        statement = statement.where(
            or_(
                User.display_name.icontains(owner_query, autoescape=True),
                User.email.icontains(owner_query, autoescape=True),
            )
        )
    if name_query:
        statement = statement.where(Template.name.icontains(name_query, autoescape=True))
    if deleted_after is not None:
        statement = statement.where(Template.deleted_at >= deleted_after)
    if deleted_before is not None:
        statement = statement.where(Template.deleted_at < deleted_before)
    statement = statement.order_by(Template.deleted_at, Template.id).limit(limit).offset(offset)
    return [
        DeletedTemplateRow(
            template,
            owner_name,
            count,
            reason if action == ModerationActionKind.DELETE else None,
        )
        for template, owner_name, count, reason, action in session.execute(statement)
    ]


def list_moderation_actions(
    session: Session,
    limit: int,
    offset: int,
    actor_id: uuid.UUID | None,
    target: str | None,
    account_id: uuid.UUID | None = None,
) -> list[ModerationAction]:
    statement: Select[ModerationAction] = select(ModerationAction)
    if account_id is not None:
        statement = statement.where(
            or_(
                ModerationAction.target_id == account_id,
                ModerationAction.target_id.in_(
                    select(Template.id).where(Template.owner_id == account_id)
                ),
                ModerationAction.target_id.in_(
                    select(Image.id).where(Image.owner_id == account_id)
                ),
            )
        )
    if actor_id is not None:
        statement = statement.where(ModerationAction.actor_id == actor_id)
    if target:
        statement = statement.where(
            ModerationAction.target_label.icontains(target, autoescape=True)
        )
    statement = (
        statement.order_by(ModerationAction.created_at.desc(), ModerationAction.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())
