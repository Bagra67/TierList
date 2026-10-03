import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email)).one_or_none()


def add_user(session: Session, user: User) -> None:
    session.add(user)
    # Flush : déclenche tout de suite la contrainte d'unicité de l'email
    session.flush()


def delete_user(session: Session, user: User) -> None:
    # Les refresh tokens sont supprimés par la base (ON DELETE CASCADE)
    session.delete(user)
