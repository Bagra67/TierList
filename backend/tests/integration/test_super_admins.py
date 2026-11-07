from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.exceptions.auth import UserNotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.services.super_admins import set_super_admin
from tests.integration.helpers import register

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(db_session: Session) -> User:
    user: User = User(email="alice@example.com", display_name="Alice")
    db_session.add(user)
    db_session.flush()
    return user


def test_granting_makes_the_account_a_super_admin(db_session: Session, alice: User):
    role: UserRole = set_super_admin(
        lambda: nullcontext(db_session), "alice@example.com", granted=True
    )

    assert role == UserRole.SUPER_ADMIN
    db_session.refresh(alice)
    assert alice.is_super_admin


def test_revoking_gives_the_user_role_back(db_session: Session, alice: User):
    alice.role = UserRole.SUPER_ADMIN
    db_session.flush()

    role: UserRole = set_super_admin(
        lambda: nullcontext(db_session), "alice@example.com", granted=False
    )

    assert role == UserRole.USER
    db_session.refresh(alice)
    assert alice.role == UserRole.USER


def test_the_email_is_found_whatever_its_case(db_session: Session, alice: User):
    set_super_admin(lambda: nullcontext(db_session), "  Alice@Example.COM ", granted=True)

    db_session.refresh(alice)
    assert alice.is_super_admin


def test_an_unknown_email_is_refused(db_session: Session, alice: User):
    with pytest.raises(UserNotFoundError):
        set_super_admin(lambda: nullcontext(db_session), "bob@example.com", granted=True)

    db_session.refresh(alice)
    assert alice.role == UserRole.USER


def test_me_shows_the_role_once_granted(auth_client: TestClient, db_session: Session):
    headers: dict[str, str] = register(auth_client, "carol@example.com")

    set_super_admin(lambda: nullcontext(db_session), "carol@example.com", granted=True)
    response: Response = auth_client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["role"] == "super_admin"
