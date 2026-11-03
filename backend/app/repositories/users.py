import uuid

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_user_for_update(session: Session, user_id: uuid.UUID) -> User | None:
    """Le compte, verrouillé jusqu'à la fin de la transaction (bannissement)."""
    return session.get(User, user_id, with_for_update=True)


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


def search_users(session: Session, query: str | None, limit: int, offset: int) -> list[User]:
    """Comptes dont le nom ou l'e-mail contient query (sans casse ; % et _ y sont des caractères
    ordinaires), par nom ; tous les comptes sans query. L'identifiant départage deux noms égaux :
    une page ne saute rien."""
    statement: Select[User] = select(User)
    if query:
        statement = statement.where(
            or_(
                User.display_name.icontains(query, autoescape=True),
                User.email.icontains(query, autoescape=True),
            )
        )
    statement = statement.order_by(User.display_name, User.id).limit(limit).offset(offset)
    return list(session.scalars(statement).all())
