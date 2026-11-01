import uuid
from datetime import datetime

from sqlalchemy import Select, delete, select
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


def list_moderation_actions(
    session: Session,
    limit: int,
    offset: int,
    actor_id: uuid.UUID | None,
    target: str | None,
) -> list[ModerationAction]:
    """Entrées du journal, de la plus récente à la plus ancienne, filtrées par super admin et par
    un texte cherché dans le libellé de la cible (sans casse ; % et _ y sont des caractères
    ordinaires)."""
    statement: Select[ModerationAction] = select(ModerationAction)
    if actor_id is not None:
        statement = statement.where(ModerationAction.actor_id == actor_id)
    if target:
        statement = statement.where(
            ModerationAction.target_label.icontains(target, autoescape=True)
        )
    statement = (
        # L'identifiant départage deux entrées du même instant : une page ne saute rien
        statement.order_by(ModerationAction.created_at.desc(), ModerationAction.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())
