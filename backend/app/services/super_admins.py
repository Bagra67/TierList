import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.core.email_addresses import normalize_email
from app.exceptions.auth import UserNotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories import users as user_repository

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractContextManager[Session]]


def set_super_admin(session_factory: SessionFactory, email: str, *, granted: bool) -> UserRole:
    role: UserRole = UserRole.SUPER_ADMIN if granted else UserRole.USER
    with session_factory() as session:
        user: User | None = user_repository.get_user_by_email(session, normalize_email(email))
        if user is None:
            raise UserNotFoundError
        user.role = role
        session.commit()
        logger.info("Rôle changé : user_id=%s role=%s", user.id, role)
        return role
