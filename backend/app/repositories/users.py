import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
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


def list_super_admins(session: Session) -> list[User]:
    """Comptes super admin, par nom (le filtre « Super admin » du journal de modération)."""
    return list(
        session.scalars(
            select(User).where(User.role == UserRole.SUPER_ADMIN).order_by(User.display_name)
        ).all()
    )
