from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_google_oauth_client
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.core.security import create_access_token
from app.exceptions.google import GoogleAuthError
from app.main import app
from app.models.user import OAuthAccount, User
from app.services.email import Email
from app.services.google_oauth import GoogleIdentity, GoogleLoginAttempt
from app.services.google_oauth import GoogleOAuthClient as RealGoogleOAuthClient
from tests.integration.helpers import link_token

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
ALICE_GOOGLE = GoogleIdentity(
    subject="google-subject-123",
    email="Alice@Gmail.com",
    email_verified=True,
    name="Alice Martin",
)


class FakeGoogleOAuthClient(RealGoogleOAuthClient):
    """Client Google sans réseau : renvoie l'identité choisie par le test, ou une erreur."""

    def __init__(self) -> None:
        super().__init__(
            "test-client-id",
            "test-client-secret",
            "http://testserver/callback",
            http_timeout_seconds=10,
        )
        self.identity: GoogleIdentity | None = ALICE_GOOGLE
        self.received_codes: list[str] = []

    def fetch_identity(self, code: str, attempt: GoogleLoginAttempt) -> GoogleIdentity:
        self.received_codes.append(code)
        if self.identity is None:
            raise GoogleAuthError("id_token invalide")
        return self.identity


@pytest.fixture
def google() -> FakeGoogleOAuthClient:
    return FakeGoogleOAuthClient()


@pytest.fixture
def google_client(auth_client: TestClient, google: FakeGoogleOAuthClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_google_oauth_client] = lambda: google
    try:
        yield auth_client
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)


def start_google_login(client: TestClient, query: str = "") -> str:
    """Démarre la connexion et renvoie le state envoyé à Google."""
    response = client.get(f"/auth/google/login{query}", follow_redirects=False)
    assert response.status_code == 302
    assert "google_login" in response.cookies
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def google_callback(client: TestClient, query: str):
    return client.get(f"/auth/google/callback?{query}", follow_redirects=False)


def sign_in_with_google(client: TestClient, login_query: str = ""):
    state = start_google_login(client, login_query)
    return google_callback(client, f"code=auth-code&state={state}")


def current_user(client: TestClient) -> dict[str, object]:
    refreshed = client.post("/auth/refresh")
    assert refreshed.status_code == 200
    access_token = refreshed.json()["access_token"]
    return client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"}).json()


def test_login_redirects_to_google_with_a_signed_attempt_cookie(google_client: TestClient):
    response = google_client.get("/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/")
    set_cookie = response.headers["set-cookie"]
    expected = ("google_login=", "HttpOnly", "SameSite=lax", "Path=/auth/google", "Max-Age=600")
    for attribute in expected:
        assert attribute in set_cookie


def test_attempt_cookie_lifetime_follows_the_settings(
    google_client: TestClient, override_settings: Callable[..., None]
):
    override_settings(google_login_attempt_ttl_minutes=2)

    response = google_client.get("/auth/google/login", follow_redirects=False)

    assert "Max-Age=120" in response.headers["set-cookie"]


def test_first_google_sign_in_creates_an_account_without_password(
    google_client: TestClient, google: FakeGoogleOAuthClient, db_session: Session
):
    response = sign_in_with_google(google_client)

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert google.received_codes == ["auth-code"]
    user = current_user(google_client)
    assert user["email"] == "alice@gmail.com"
    assert user["display_name"] == "Alice Martin"
    assert user["has_password"] is False
    account = db_session.scalars(select(OAuthAccount)).one()
    assert (account.provider, account.provider_subject) == ("google", "google-subject-123")


def test_next_google_sign_in_reuses_the_same_account(
    google_client: TestClient, google: FakeGoogleOAuthClient, db_session: Session
):
    sign_in_with_google(google_client)
    # L'email Google a changé : c'est l'identifiant « sub » qui retrouve le compte
    google.identity = GoogleIdentity(
        subject=ALICE_GOOGLE.subject, email="alice.new@gmail.com", email_verified=True, name=None
    )

    response = sign_in_with_google(google_client)

    assert response.headers["location"] == "/"
    assert len(db_session.scalars(select(User)).all()) == 1
    assert current_user(google_client)["email"] == "alice@gmail.com"


def test_google_identity_is_linked_to_an_existing_verified_account(
    google_client: TestClient, db_session: Session, sent_emails: list[Email]
):
    registration = {"email": "alice@gmail.com", "password": PASSWORD, "display_name": "Alice"}
    assert google_client.post("/auth/register", json=registration).status_code == 201
    token = link_token(sent_emails[0])
    assert google_client.post("/auth/email/verify", json={"token": token}).status_code == 204
    google_client.cookies.clear()

    response = sign_in_with_google(google_client)

    assert response.headers["location"] == "/"
    user = current_user(google_client)
    assert user["display_name"] == "Alice"
    assert user["has_password"] is True
    assert (
        db_session.scalars(select(OAuthAccount)).one().user_id
        == db_session.scalars(select(User)).one().id
    )


def test_google_takes_over_an_unverified_account_and_drops_its_password(
    google_client: TestClient, db_session: Session
):
    # Quelqu'un s'inscrit avec l'adresse Gmail d'Alice sans pouvoir la confirmer
    registration = {"email": "alice@gmail.com", "password": PASSWORD, "display_name": "Mallory"}
    assert google_client.post("/auth/register", json=registration).status_code == 201
    squatter_refresh_token = google_client.cookies["refresh_token"]
    google_client.cookies.clear()

    response = sign_in_with_google(google_client)

    assert response.headers["location"] == "/"
    user = current_user(google_client)
    assert user["has_password"] is False
    assert user["email_verified"] is True
    # Le mot de passe posé par l'inconnu ne permet plus de se connecter
    login = google_client.post(
        "/auth/login", json={"email": "alice@gmail.com", "password": PASSWORD}
    )
    assert login.status_code == 401
    # Et sa session ouverte est fermée
    google_client.cookies.clear()
    google_client.cookies.set("refresh_token", squatter_refresh_token)
    assert google_client.post("/auth/refresh").status_code == 401
    assert db_session.scalars(select(OAuthAccount)).one().user_id == (
        db_session.scalars(select(User)).one().id
    )


@pytest.mark.parametrize("existing_account", [True, False], ids=["existing-email", "new-email"])
def test_unverified_google_email_is_refused(
    google_client: TestClient,
    google: FakeGoogleOAuthClient,
    db_session: Session,
    existing_account: bool,
):
    if existing_account:
        registration = {"email": "alice@gmail.com", "password": PASSWORD, "display_name": "Alice"}
        google_client.post("/auth/register", json=registration)
        google_client.cookies.clear()
    google.identity = GoogleIdentity(
        subject="google-subject-123", email="alice@gmail.com", email_verified=False, name=None
    )

    response = sign_in_with_google(google_client)

    assert response.headers["location"] == "/login?error=google_email_not_verified"
    assert "refresh_token" not in google_client.cookies
    assert db_session.scalars(select(OAuthAccount)).all() == []


def test_callback_with_another_state_is_refused(google_client: TestClient):
    start_google_login(google_client)

    response = google_callback(google_client, "code=auth-code&state=forged-state")

    assert response.headers["location"] == "/login?error=google_failed"
    assert "refresh_token" not in google_client.cookies


def test_callback_without_attempt_cookie_is_refused(google_client: TestClient):
    response = google_callback(google_client, "code=auth-code&state=some-state")

    assert response.headers["location"] == "/login?error=google_failed"


def test_callback_with_an_invalid_id_token_is_refused(
    google_client: TestClient, google: FakeGoogleOAuthClient
):
    google.identity = None

    response = sign_in_with_google(google_client)

    assert response.headers["location"] == "/login?error=google_failed"
    # La tentative ne sert qu'une fois : son cookie est effacé
    assert "google_login" not in google_client.cookies


@pytest.mark.parametrize(
    ("google_error", "error_code"),
    [("access_denied", "google_cancelled"), ("server_error", "google_failed")],
)
def test_error_returned_by_google_is_reported(
    google_client: TestClient, google_error: str, error_code: str
):
    start_google_login(google_client)

    response = google_callback(google_client, f"error={google_error}")

    assert response.headers["location"] == f"/login?error={error_code}"


def test_google_sign_in_is_unavailable_when_not_configured(auth_client: TestClient):
    app.dependency_overrides[get_google_oauth_client] = lambda: None
    try:
        login = auth_client.get("/auth/google/login", follow_redirects=False)
        callback = google_callback(auth_client, "code=auth-code&state=some-state")
    finally:
        app.dependency_overrides.pop(get_google_oauth_client, None)

    assert login.headers["location"] == "/login?error=google_unavailable"
    assert callback.headers["location"] == "/login?error=google_unavailable"


def test_sign_in_can_resume_the_account_deletion(google_client: TestClient):
    response = sign_in_with_google(google_client, "?next=delete-account")

    assert response.headers["location"] == "/?confirm=delete-account"


def test_unknown_next_step_is_rejected(google_client: TestClient):
    response = google_client.get(
        "/auth/google/login?next=https://evil.example.com", follow_redirects=False
    )

    assert response.status_code == 422


def test_password_sign_in_is_refused_for_a_google_only_account(google_client: TestClient):
    sign_in_with_google(google_client)

    response = google_client.post(
        "/auth/login", json={"email": "alice@gmail.com", "password": PASSWORD}
    )

    assert response.status_code == 401


def google_only_access_token(db_session: Session, signed_in_ago: timedelta) -> str:
    user = db_session.scalars(select(User)).one()
    return create_access_token(
        user_id=user.id,
        auth_time=datetime.now(UTC) - signed_in_ago,
        secret_key=get_settings().jwt_secret_key.get_secret_value(),
        ttl=timedelta(minutes=15),
    )


def test_google_only_account_is_deleted_after_a_recent_sign_in(
    google_client: TestClient, db_session: Session
):
    sign_in_with_google(google_client)
    access_token = google_only_access_token(db_session, signed_in_ago=timedelta(minutes=1))

    response = google_client.request(
        "DELETE", "/auth/me", json={}, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 204
    assert db_session.scalars(select(User)).all() == []
    assert db_session.scalars(select(OAuthAccount)).all() == []


def test_google_only_account_deletion_requires_a_recent_sign_in(
    google_client: TestClient, db_session: Session
):
    sign_in_with_google(google_client)
    access_token = google_only_access_token(db_session, signed_in_ago=timedelta(minutes=10))

    response = google_client.request(
        "DELETE", "/auth/me", json={}, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": messages.REAUTHENTICATION_REQUIRED,
        "code": ErrorCode.REAUTHENTICATION_REQUIRED,
    }
    assert db_session.scalars(select(User)).one().email == "alice@gmail.com"


def test_recent_sign_in_delay_follows_the_settings(
    google_client: TestClient, db_session: Session, override_settings: Callable[..., None]
):
    sign_in_with_google(google_client)
    override_settings(recent_authentication_max_age_minutes=15)
    access_token = google_only_access_token(db_session, signed_in_ago=timedelta(minutes=10))

    response = google_client.request(
        "DELETE", "/auth/me", json={}, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 204
