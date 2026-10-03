import json
from collections.abc import Callable
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.core.security import create_access_token, create_email_verification_token
from app.models.user import User
from app.services.email import Email
from tests.integration.helpers import link_token

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
REGISTRATION = {"email": "Alice@Example.com", "password": PASSWORD, "display_name": "Alice"}


def register(client: TestClient, **changes: str) -> str:
    response = client.post("/auth/register", json={**REGISTRATION, **changes})
    assert response.status_code == 201
    return response.json()["access_token"]


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def me(client: TestClient, access_token: str) -> dict[str, object]:
    return client.get("/auth/me", headers=bearer(access_token)).json()


def signed_token(user: User, **changes: object) -> str:
    claims: dict[str, object] = {
        "user_id": user.id,
        "email": user.email,
        "secret_key": get_settings().jwt_secret_key.get_secret_value(),
        "ttl": timedelta(hours=24),
        **changes,
    }
    return create_email_verification_token(**claims)  # pyright: ignore[reportArgumentType]


def test_registration_sends_a_verification_link(auth_client: TestClient, sent_emails: list[Email]):
    access_token = register(auth_client)

    [email] = sent_emails
    assert email.to == "alice@example.com"
    assert email.subject == "Confirmez votre adresse email"
    assert "Bonjour Alice," in email.text
    assert "http://localhost:5173/verify-email?token=" in email.text
    assert me(auth_client, access_token)["email_verified"] is False


def test_the_link_does_not_reveal_the_address(auth_client: TestClient, sent_emails: list[Email]):
    register(auth_client)

    # Un JWT se lit sans la clé : l'adresse ne doit pas y figurer en clair
    claims = jwt.decode(link_token(sent_emails[0]), options={"verify_signature": False})

    assert "alice@example.com" not in json.dumps(claims)


def test_verification_email_follows_the_interface_language(
    auth_client: TestClient, sent_emails: list[Email]
):
    register(auth_client, language="en")

    assert sent_emails[0].subject == "Confirm your email address"
    assert "Hello Alice," in sent_emails[0].text


def test_display_name_is_escaped_in_the_html_email(
    auth_client: TestClient, sent_emails: list[Email]
):
    register(auth_client, display_name="<b>Bob</b>")

    assert "&lt;b&gt;Bob&lt;/b&gt;" in sent_emails[0].html
    assert "<b>Bob</b>" not in sent_emails[0].html


def test_the_link_confirms_the_address_and_can_be_reused(
    auth_client: TestClient, sent_emails: list[Email]
):
    access_token = register(auth_client)
    token = link_token(sent_emails[0])

    first = auth_client.post("/auth/email/verify", json={"token": token})
    again = auth_client.post("/auth/email/verify", json={"token": token})

    assert first.status_code == 204
    assert again.status_code == 204
    assert me(auth_client, access_token)["email_verified"] is True


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda user: "not-a-jwt", id="not-a-jwt"),
        pytest.param(lambda user: signed_token(user, ttl=timedelta(seconds=-1)), id="expired"),
        pytest.param(lambda user: signed_token(user, email="old@example.com"), id="email-changed"),
        pytest.param(
            lambda user: signed_token(user, secret_key="another-secret-key-of-32-characters"),
            id="other-key",
        ),
        pytest.param(
            lambda user: create_access_token(
                user_id=user.id,
                auth_time=user.created_at,
                secret_key=get_settings().jwt_secret_key.get_secret_value(),
                ttl=timedelta(minutes=15),
            ),
            id="access-token",
        ),
    ],
)
def test_invalid_links_are_refused(
    auth_client: TestClient, db_session: Session, make_token: Callable[[User], str]
):
    access_token = register(auth_client)
    user = db_session.scalars(select(User)).one()

    response = auth_client.post("/auth/email/verify", json={"token": make_token(user)})

    assert response.status_code == 400
    assert response.json() == {"detail": messages.INVALID_TOKEN, "code": ErrorCode.INVALID_TOKEN}
    assert me(auth_client, access_token)["email_verified"] is False


def test_resending_requires_a_session(auth_client: TestClient):
    response = auth_client.post("/auth/email/verification", json={})

    assert response.status_code == 401


def test_resending_too_soon_sends_nothing(auth_client: TestClient, sent_emails: list[Email]):
    access_token = register(auth_client)

    response = auth_client.post("/auth/email/verification", json={}, headers=bearer(access_token))

    assert response.status_code == 204
    assert len(sent_emails) == 1


def test_resending_after_the_cooldown_sends_a_new_link(
    auth_client: TestClient,
    sent_emails: list[Email],
    override_settings: Callable[..., None],
):
    access_token = register(auth_client)
    override_settings(email_cooldown_seconds=0)

    response = auth_client.post(
        "/auth/email/verification", json={"language": "en"}, headers=bearer(access_token)
    )

    assert response.status_code == 204
    assert len(sent_emails) == 2
    assert sent_emails[1].subject == "Confirm your email address"


def test_nothing_is_resent_once_the_address_is_confirmed(
    auth_client: TestClient,
    sent_emails: list[Email],
    override_settings: Callable[..., None],
):
    access_token = register(auth_client)
    auth_client.post("/auth/email/verify", json={"token": link_token(sent_emails[0])})
    override_settings(email_cooldown_seconds=0)

    response = auth_client.post("/auth/email/verification", json={}, headers=bearer(access_token))

    assert response.status_code == 204
    assert len(sent_emails) == 1
