import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, Select, and_, or_, select
from sqlalchemy.orm import Session

from app.models.account_ban import AccountBan


def is_active(now: datetime) -> ColumnElement[bool]:
    """Un bannissement est actif s'il n'est pas levé et que sa fin, s'il en a une, n'est pas
    passée : un bannissement temporaire finit seul, sans tâche planifiée."""
    return and_(
        AccountBan.lifted_at.is_(None),
        or_(AccountBan.ends_at.is_(None), AccountBan.ends_at > now),
    )


def add_ban(session: Session, ban: AccountBan) -> None:
    session.add(ban)


def get_active_ban(session: Session, user_id: uuid.UUID, now: datetime) -> AccountBan | None:
    """Le bannissement actif du compte. Il y en a au plus un : bannir un compte déjà banni lève
    d'abord le bannissement en cours."""
    statement: Select[AccountBan] = select(AccountBan).where(
        AccountBan.user_id == user_id, is_active(now)
    )
    return session.scalars(statement).one_or_none()


def banned_user_ids(session: Session, user_ids: list[uuid.UUID], now: datetime) -> set[uuid.UUID]:
    """Parmi ces comptes, ceux qui ont un bannissement actif, en une requête."""
    statement: Select[uuid.UUID] = select(AccountBan.user_id).where(
        AccountBan.user_id.in_(user_ids), is_active(now)
    )
    return set(session.scalars(statement).all())
