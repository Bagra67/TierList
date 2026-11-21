import uuid

from sqlalchemy import Select, delete, exists, select
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.orm import Session

from app.models.template_favorite import TemplateFavorite


def add_favorite(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> None:
    statement: Insert = (
        insert(TemplateFavorite)
        .values(template_id=template_id, user_id=user_id)
        .on_conflict_do_nothing(
            index_elements=[TemplateFavorite.template_id, TemplateFavorite.user_id]
        )
    )
    session.execute(statement)


def remove_favorite(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> None:
    session.execute(
        delete(TemplateFavorite).where(
            TemplateFavorite.template_id == template_id, TemplateFavorite.user_id == user_id
        )
    )


def has_favorited(session: Session, template_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    statement: Select[bool] = select(
        exists().where(
            TemplateFavorite.template_id == template_id, TemplateFavorite.user_id == user_id
        )
    )
    return bool(session.scalar(statement))


def list_favorited_template_ids(
    session: Session, user_id: uuid.UUID, template_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    statement: Select[uuid.UUID] = select(TemplateFavorite.template_id).where(
        TemplateFavorite.user_id == user_id, TemplateFavorite.template_id.in_(template_ids)
    )
    return set(session.scalars(statement))
