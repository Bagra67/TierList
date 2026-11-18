import uuid

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.orm import Session

from app.models.template_like import TemplateLike


def add_like(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> None:
    statement: Insert = (
        insert(TemplateLike)
        .values(template_id=template_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=[TemplateLike.template_id, TemplateLike.user_id])
    )
    session.execute(statement)


def remove_like(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> None:
    session.execute(
        delete(TemplateLike).where(
            TemplateLike.template_id == template_id, TemplateLike.user_id == user_id
        )
    )


def count_likes(session: Session, template_id: uuid.UUID) -> int:
    statement: Select[int] = select(func.count()).where(TemplateLike.template_id == template_id)
    return session.scalar(statement) or 0


def has_liked(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    statement: Select[bool] = select(
        exists().where(TemplateLike.template_id == template_id, TemplateLike.user_id == user_id)
    )
    return bool(session.scalar(statement))
