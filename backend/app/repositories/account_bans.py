import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, Select, and_, not_, or_, select
from sqlalchemy.orm import Session

from app.models.account_ban import AccountBan


def is_active(now: datetime) -> ColumnElement[bool]:
    return and_(
        AccountBan.lifted_at.is_(None),
        or_(AccountBan.ends_at.is_(None), AccountBan.ends_at > now),
    )


def add_ban(session: Session, ban: AccountBan) -> None:
    session.add(ban)


def get_active_ban(session: Session, user_id: uuid.UUID, now: datetime) -> AccountBan | None:
    statement: Select[AccountBan] = select(AccountBan).where(
        AccountBan.user_id == user_id, is_active(now)
    )
    return session.scalars(statement).one_or_none()


def list_past_bans(session: Session, user_id: uuid.UUID, now: datetime) -> list[AccountBan]:
    statement: Select[AccountBan] = (
        select(AccountBan)
        .where(AccountBan.user_id == user_id, not_(is_active(now)))
        .order_by(AccountBan.created_at.desc(), AccountBan.id)
    )
    return list(session.scalars(statement).all())


def banned_user_ids(session: Session, user_ids: list[uuid.UUID], now: datetime) -> set[uuid.UUID]:
    statement: Select[uuid.UUID] = select(AccountBan.user_id).where(
        AccountBan.user_id.in_(user_ids), is_active(now)
    )
    return set(session.scalars(statement).all())
