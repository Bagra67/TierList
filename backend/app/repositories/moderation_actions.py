import uuid
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import ReturningDelete

from app.models.moderation_action import ModerationAction


def add_moderation_action(session: Session, moderation_action: ModerationAction) -> None:
    session.add(moderation_action)


def delete_moderation_actions_before(session: Session, limit: datetime) -> int:
    """Supprime les entrées du journal écrites avant limit ; renvoie leur nombre."""
    statement: ReturningDelete[uuid.UUID] = (
        delete(ModerationAction)
        .where(ModerationAction.created_at < limit)
        .returning(ModerationAction.id)
    )
    return len(session.scalars(statement).all())
