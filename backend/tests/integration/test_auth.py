from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.core.security import hash_refresh_token
from app.main import app
from app.models.user import RefreshToken, User

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
REGISTRATION = {"email": "Alice@Example.com", "password": PASSWORD, "display_name": "Alice"}


def register(client: TestClient) -> str:
    response = client.post("/auth/register", json=REGISTRATION)
    assert response.status_code == 201
    return response.json()["access_token"]


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_register_creates_the_account_and_returns_tokens(
    auth_client: TestClient, db_session: Session
):
    response = auth_client.post("/auth/register", json=REGISTRATION)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert "refresh_token" in response.cookies

    user = db_session.scalars(select(User)).one()
    assert user.email == "alice@example.com"
    assert user.password_hash != PASSWORD
    stored = db_session.scalars(select(RefreshToken)).one()
    # Seul le hash est en base, jamais le token lui-même
    assert stored.token_hash == hash_refresh_token(response.cookies["refresh_token"])


def test_register_rejects_an_email_already_used_whatever_its_case(auth_client: TestClient):
    register(auth_client)

    response = auth_client.post(
        "/auth/register", json={**REGISTRATION, "email": "ALICE@example.COM"}
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": messages.EMAIL_ALREADY_REGISTERED,
        "code": ErrorCode.EMAIL_ALREADY_REGISTERED,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [("email", "not-an-email"), ("password", "short"), ("display_name", "   ")],
)
def test_register_validates_its_input(auth_client: TestClient, field: str, value: str):
    response = auth_client.post("/auth/register", json={**REGISTRATION, field: value})

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["errors"]] == [f"body.{field}"]


def test_short_password_error_states_the_minimum(auth_client: TestClient):
    response = auth_client.post("/auth/register", json={**REGISTRATION, "password": "short"})

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {
            "field": "body.password",
            "message": messages.PASSWORD_TOO_SHORT.format(min_length=8),
            "code": ErrorCode.PASSWORD_TOO_SHORT,
            "params": {"min_length": 8},
        }
    ]


@pytest.fixture
def password_min_length_12(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Le schéma lit get_settings() directement (pas par injection) : on passe par
    # l'environnement, et on vide le cache des réglages avant et après le test.
    monkeypatch.setenv("PASSWORD_MIN_LENGTH", "12")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.usefixtures("password_min_length_12")
def test_password_min_length_is_configurable(auth_client: TestClient):
    ten_characters = "abcdefghij"

    too_short = auth_client.post(
        "/auth/register", json={**REGISTRATION, "password": ten_characters}
    )
    long_enough = auth_client.post(
        "/auth/register", json={**REGISTRATION, "password": ten_characters + "kl"}
    )

    assert too_short.status_code == 422
    assert too_short.json()["errors"] == [
        {
            "field": "body.password",
            "message": "The password must be at least 12 characters long",
            "code": "password_too_short",
            "params": {"min_length": 12},
        }
    ]
    assert long_enough.status_code == 201


def test_me_returns_the_authenticated_user(auth_client: TestClient):
    access_token = register(auth_client)

    response = auth_client.get("/auth/me", headers=bearer(access_token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice"
    assert "password_hash" not in body


@pytest.mark.parametrize(
    "headers",
    [pytest.param({}, id="no-token"), pytest.param(bearer("not-a-jwt"), id="invalid-token")],
)
def test_me_requires_a_valid_access_token(auth_client: TestClient, headers: dict[str, str]):
    response = auth_client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": messages.NOT_AUTHENTICATED,
        "code": ErrorCode.NOT_AUTHENTICATED,
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_with_valid_credentials(auth_client: TestClient):
    register(auth_client)
    auth_client.cookies.clear()

    response = auth_client.post(
        "/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert "refresh_token" in response.cookies
    me = auth_client.get("/auth/me", headers=bearer(response.json()["access_token"]))
    assert me.status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param(
            {"email": "alice@example.com", "password": "wrong password"}, id="bad-password"
        ),
        pytest.param({"email": "nobody@example.com", "password": PASSWORD}, id="unknown-email"),
    ],
)
def test_login_failures_are_indistinguishable(auth_client: TestClient, credentials: dict[str, str]):
    register(auth_client)

    response = auth_client.post("/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json() == {
        "detail": messages.INVALID_CREDENTIALS,
        "code": ErrorCode.INVALID_CREDENTIALS,
    }


def test_refresh_rotates_the_refresh_token(auth_client: TestClient):
    register(auth_client)
    first_refresh_token = auth_client.cookies["refresh_token"]

    response = auth_client.post("/auth/refresh")

    assert response.status_code == 200
    assert auth_client.cookies["refresh_token"] != first_refresh_token
    me = auth_client.get("/auth/me", headers=bearer(response.json()["access_token"]))
    assert me.status_code == 200


def test_replaying_a_rotated_refresh_token_revokes_the_whole_family(auth_client: TestClient):
    register(auth_client)
    stolen_refresh_token = auth_client.cookies["refresh_token"]
    assert auth_client.post("/auth/refresh").status_code == 200
    legitimate_refresh_token = auth_client.cookies["refresh_token"]

    auth_client.cookies.set("refresh_token", stolen_refresh_token, path="/auth")
    replay = auth_client.post("/auth/refresh")

    assert replay.status_code == 401
    assert replay.json() == {"detail": messages.SESSION_EXPIRED, "code": ErrorCode.SESSION_EXPIRED}
    # Le token le plus récent, même légitime, est révoqué lui aussi
    auth_client.cookies.set("refresh_token", legitimate_refresh_token, path="/auth")
    assert auth_client.post("/auth/refresh").status_code == 401


def test_expired_refresh_token_is_rejected(auth_client: TestClient, db_session: Session):
    register(auth_client)
    stored = db_session.scalars(select(RefreshToken)).one()
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response = auth_client.post("/auth/refresh")

    assert response.status_code == 401


def test_sign_in_deletes_the_expired_refresh_tokens(auth_client: TestClient, db_session: Session):
    register(auth_client)
    expired = db_session.scalars(select(RefreshToken)).one()
    expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()
    expired_id = expired.id
    auth_client.cookies.clear()
    login = {"email": "alice@example.com", "password": PASSWORD}
    assert auth_client.post("/auth/login", json=login).status_code == 200
    # Révoqué mais pas expiré : gardé, pour repérer une réutilisation
    assert auth_client.post("/auth/logout").status_code == 204
    revoked_id = db_session.scalars(select(RefreshToken)).one().id

    assert auth_client.post("/auth/login", json=login).status_code == 200

    remaining_ids = set(db_session.scalars(select(RefreshToken.id)).all())
    assert expired_id not in remaining_ids
    assert revoked_id in remaining_ids
    assert len(remaining_ids) == 2


def test_unknown_refresh_token_is_rejected_and_clears_the_cookie(auth_client: TestClient):
    auth_client.cookies.set("refresh_token", "unknown", path="/auth")

    response = auth_client.post("/auth/refresh")

    assert response.status_code == 401
    assert 'refresh_token=""' in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_revokes_the_session(auth_client: TestClient):
    register(auth_client)
    refresh_token = auth_client.cookies["refresh_token"]

    response = auth_client.post("/auth/logout")

    assert response.status_code == 204
    assert "refresh_token" not in auth_client.cookies
    auth_client.cookies.set("refresh_token", refresh_token, path="/auth")
    assert auth_client.post("/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_rejected(auth_client: TestClient):
    assert auth_client.post("/auth/refresh").status_code == 401


def test_logout_without_session_succeeds(auth_client: TestClient):
    assert auth_client.post("/auth/logout").status_code == 204


def test_refresh_cookie_attributes(client: TestClient):
    # Paramètres par défaut (production) : Secure, HttpOnly, SameSite=Strict, chemin /api/auth
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(
        update={"auth_cookie_secure": True, "auth_cookie_path": "/api/auth"}
    )
    try:
        response = client.post("/auth/register", json=REGISTRATION)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith("refresh_token=")
    for attribute in ("HttpOnly", "Secure", "SameSite=strict", "Path=/api/auth", "Max-Age=2592000"):
        assert attribute in set_cookie


def delete_account(client: TestClient, access_token: str, password: str):
    # TestClient.delete n'accepte pas de corps : on passe par request()
    return client.request(
        "DELETE", "/auth/me", json={"password": password}, headers=bearer(access_token)
    )


def test_delete_account_removes_the_user_and_its_sessions(
    auth_client: TestClient, db_session: Session
):
    access_token = register(auth_client)
    refresh_token = auth_client.cookies["refresh_token"]

    response = delete_account(auth_client, access_token, PASSWORD)

    assert response.status_code == 204
    assert "refresh_token" not in auth_client.cookies
    assert db_session.scalars(select(User)).all() == []
    assert db_session.scalars(select(RefreshToken)).all() == []
    # Plus aucune session ni connexion possible
    assert auth_client.get("/auth/me", headers=bearer(access_token)).status_code == 401
    auth_client.cookies.set("refresh_token", refresh_token, path="/auth")
    assert auth_client.post("/auth/refresh").status_code == 401
    login = auth_client.post(
        "/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
    )
    assert login.status_code == 401


def test_delete_account_requires_the_right_password(auth_client: TestClient, db_session: Session):
    access_token = register(auth_client)

    response = delete_account(auth_client, access_token, "wrong password")

    assert response.status_code == 403
    assert response.json() == {
        "detail": messages.INCORRECT_PASSWORD,
        "code": ErrorCode.INCORRECT_PASSWORD,
    }
    assert db_session.scalars(select(User)).one().email == "alice@example.com"


def test_delete_account_requires_an_access_token(auth_client: TestClient):
    register(auth_client)

    response = auth_client.request("DELETE", "/auth/me", json={"password": PASSWORD})

    assert response.status_code == 401


def test_delete_account_without_password_is_refused_for_a_password_account(
    auth_client: TestClient,
):
    access_token = register(auth_client)

    response = auth_client.request("DELETE", "/auth/me", json={}, headers=bearer(access_token))

    assert response.status_code == 403
    assert response.json() == {
        "detail": messages.INCORRECT_PASSWORD,
        "code": ErrorCode.INCORRECT_PASSWORD,
    }
