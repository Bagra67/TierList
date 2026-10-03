from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.core.security import create_password_reset_token, password_fingerprint
from app.models.user import User
from app.services.email import Email
from tests.integration.helpers import link_token

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a brand new passphrase"
REGISTRATION = {"email": "alice@example.com", "password": PASSWORD, "display_name": "Alice"}


def register(client: TestClient) -> None:
    assert client.post("/auth/register", json=REGISTRATION).status_code == 201


def forgot(client: TestClient, email: str = "alice@example.com", language: str = "fr") -> None:
    response = client.post("/auth/password/forgot", json={"email": email, "language": language})
    assert response.status_code == 204


def login(client: TestClient, password: str) -> int:
    response = client.post("/auth/login", json={"email": "alice@example.com", "password": password})
    return response.status_code


def reset_emails(sent_emails: list[Email]) -> list[Email]:
    # L'inscription envoie aussi l'email de vérification : seuls ceux de réinitialisation comptent
    return [email for email in sent_emails if "/reset-password?" in email.text]


def signed_token(user: User, **changes: object) -> str:
    secret_key = get_settings().jwt_secret_key.get_secret_value()
    claims: dict[str, object] = {
        "user_id": user.id,
        "password_fingerprint": password_fingerprint(user.password_hash, secret_key=secret_key),
        "secret_key": secret_key,
        "ttl": timedelta(minutes=30),
        **changes,
    }
    return create_password_reset_token(**claims)  # pyright: ignore[reportArgumentType]


def test_forgot_password_sends_a_reset_link(auth_client: TestClient, sent_emails: list[Email]):
    register(auth_client)

    forgot(auth_client, email="ALICE@example.com", language="en")

    [email] = reset_emails(sent_emails)
    assert email.to == "alice@example.com"
    assert email.subject == "Choose a new password"
    assert "http://localhost:5173/reset-password?token=" in email.text
    assert "30 minutes" in email.text


def test_unknown_email_gets_the_same_answer_and_no_email(
    auth_client: TestClient, sent_emails: list[Email]
):
    forgot(auth_client, email="nobody@example.com")

    assert sent_emails == []


def test_asking_again_too_soon_sends_nothing(auth_client: TestClient, sent_emails: list[Email]):
    register(auth_client)

    forgot(auth_client)
    forgot(auth_client)

    assert len(reset_emails(sent_emails)) == 1


def test_reset_replaces_the_password_and_closes_every_session(
    auth_client: TestClient, sent_emails: list[Email]
):
    register(auth_client)
    old_refresh_token = auth_client.cookies["refresh_token"]
    forgot(auth_client)
    token = link_token(reset_emails(sent_emails)[0])

    response = auth_client.post(
        "/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}
    )

    assert response.status_code == 204
    assert login(auth_client, PASSWORD) == 401
    assert login(auth_client, NEW_PASSWORD) == 200
    # La session ouverte avant la réinitialisation est fermée
    auth_client.cookies.clear()
    auth_client.cookies.set("refresh_token", old_refresh_token)
    assert auth_client.post("/auth/refresh").status_code == 401


def test_reset_confirms_the_email_address(
    auth_client: TestClient, db_session: Session, sent_emails: list[Email]
):
    register(auth_client)
    forgot(auth_client)

    auth_client.post(
        "/auth/password/reset",
        json={"token": link_token(reset_emails(sent_emails)[0]), "password": NEW_PASSWORD},
    )

    assert db_session.scalars(select(User)).one().email_verified_at is not None


def test_the_link_works_only_once(auth_client: TestClient, sent_emails: list[Email]):
    register(auth_client)
    forgot(auth_client)
    token = link_token(reset_emails(sent_emails)[0])
    auth_client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD})

    again = auth_client.post(
        "/auth/password/reset", json={"token": token, "password": "yet another passphrase"}
    )

    assert again.status_code == 400
    assert again.json() == {"detail": messages.INVALID_TOKEN, "code": ErrorCode.INVALID_TOKEN}
    assert login(auth_client, NEW_PASSWORD) == 200


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda user: "not-a-jwt", id="not-a-jwt"),
        pytest.param(lambda user: signed_token(user, ttl=timedelta(seconds=-1)), id="expired"),
        pytest.param(
            lambda user: signed_token(user, secret_key="another-secret-key-of-32-characters"),
            id="other-key",
        ),
        pytest.param(
            lambda user: signed_token(user, password_fingerprint="0" * 16), id="old-password"
        ),
    ],
)
def test_invalid_links_are_refused(
    auth_client: TestClient, db_session: Session, make_token: Callable[[User], str]
):
    register(auth_client)
    user = db_session.scalars(select(User)).one()

    response = auth_client.post(
        "/auth/password/reset", json={"token": make_token(user), "password": NEW_PASSWORD}
    )

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.INVALID_TOKEN
    assert login(auth_client, PASSWORD) == 200


def test_email_verification_link_cannot_reset_the_password(
    auth_client: TestClient, sent_emails: list[Email]
):
    register(auth_client)
    verification_token = link_token(sent_emails[0])

    response = auth_client.post(
        "/auth/password/reset", json={"token": verification_token, "password": NEW_PASSWORD}
    )

    assert response.status_code == 400


def test_new_password_must_be_long_enough(auth_client: TestClient, sent_emails: list[Email]):
    register(auth_client)
    forgot(auth_client)
    token = link_token(reset_emails(sent_emails)[0])

    response = auth_client.post("/auth/password/reset", json={"token": token, "password": "short"})

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["field"] == "body.password"
    assert error["code"] == ErrorCode.PASSWORD_TOO_SHORT


def test_account_without_password_can_set_one(
    auth_client: TestClient, db_session: Session, sent_emails: list[Email]
):
    # Compte créé avec Google : pas de mot de passe
    db_session.add(User(email="alice@example.com", password_hash=None, display_name="Alice"))
    db_session.flush()
    forgot(auth_client)

    response = auth_client.post(
        "/auth/password/reset",
        json={"token": link_token(reset_emails(sent_emails)[0]), "password": NEW_PASSWORD},
    )

    assert response.status_code == 204
    assert login(auth_client, NEW_PASSWORD) == 200
