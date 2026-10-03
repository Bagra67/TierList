import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.services.google_oauth import (
    GOOGLE_AUTHORIZATION_URL,
    GOOGLE_TOKEN_URL,
    GoogleAuthError,
    GoogleIdentity,
    GoogleLoginAttempt,
    GoogleOAuthClient,
)

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
REDIRECT_URI = "http://localhost:5173/api/auth/google/callback"
SECRET_KEY = "unit-test-secret-key-of-at-least-32-chars"

# Clés RSA générées pour les tests : elles jouent le rôle des clés de signature de Google
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StaticJWKClient(jwt.PyJWKClient):
    """Renvoie toujours la clé publique de test, sans télécharger le JWKS de Google."""

    def __init__(self) -> None:
        jwk = json.loads(RSAAlgorithm.to_jwk(GOOGLE_KEY.public_key()))
        self._signing_key = jwt.PyJWK(jwk, algorithm="RS256")

    def get_signing_key_from_jwt(self, token: str | bytes) -> jwt.PyJWK:
        return self._signing_key


def make_id_token(nonce: str, *, key: rsa.RSAPrivateKey = GOOGLE_KEY, **overrides: object) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "google-subject-123",
        "email": "alice@gmail.com",
        "email_verified": True,
        "name": "Alice Martin",
        "nonce": nonce,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="RS256")


def google_client(token_endpoint: httpx.MockTransport) -> GoogleOAuthClient:
    return GoogleOAuthClient(
        CLIENT_ID,
        "test-client-secret",
        REDIRECT_URI,
        transport=token_endpoint,
        jwk_client=StaticJWKClient(),
    )


def token_endpoint_returning(id_token: str) -> httpx.MockTransport:
    return httpx.MockTransport(lambda request: httpx.Response(200, json={"id_token": id_token}))


def test_login_attempt_round_trips_through_its_signed_cookie():
    attempt = GoogleLoginAttempt.start("delete-account")

    restored = GoogleLoginAttempt.from_cookie(attempt.to_cookie(SECRET_KEY), SECRET_KEY)

    assert restored == attempt
    assert restored.matches_state(attempt.state)
    assert not restored.matches_state("another-state")


def test_login_attempt_cookie_signed_with_another_key_is_rejected():
    cookie = GoogleLoginAttempt.start(None).to_cookie("another-secret-key-of-at-least-32-chars")

    with pytest.raises(GoogleAuthError):
        GoogleLoginAttempt.from_cookie(cookie, SECRET_KEY)


def test_code_challenge_is_the_s256_hash_of_the_verifier():
    # Exemple de la RFC 7636 (annexe B)
    attempt = GoogleLoginAttempt(
        state="s",
        nonce="n",
        code_verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        next_step=None,
    )

    assert attempt.code_challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_authorization_url_asks_for_openid_with_pkce():
    attempt = GoogleLoginAttempt.start(None)

    url = urlparse(google_client(token_endpoint_returning("")).authorization_url(attempt))
    query = {name: values[0] for name, values in parse_qs(url.query).items()}

    assert f"{url.scheme}://{url.netloc}{url.path}" == GOOGLE_AUTHORIZATION_URL
    assert query == {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": attempt.state,
        "nonce": attempt.nonce,
        "code_challenge": attempt.code_challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }


def test_fetch_identity_exchanges_the_code_and_verifies_the_id_token():
    attempt = GoogleLoginAttempt.start(None)
    received: list[httpx.Request] = []

    def token_endpoint(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(200, json={"id_token": make_id_token(attempt.nonce)})

    identity = google_client(httpx.MockTransport(token_endpoint)).fetch_identity(
        "auth-code", attempt
    )

    assert identity == GoogleIdentity(
        subject="google-subject-123",
        email="alice@gmail.com",
        email_verified=True,
        name="Alice Martin",
    )
    request = received[0]
    assert str(request.url) == GOOGLE_TOKEN_URL
    form = {name: values[0] for name, values in parse_qs(request.content.decode()).items()}
    assert form == {
        "code": "auth-code",
        "client_id": CLIENT_ID,
        "client_secret": "test-client-secret",
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": attempt.code_verifier,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"aud": "another-client-id"}, id="other-audience"),
        pytest.param({"iss": "https://evil.example.com"}, id="other-issuer"),
        pytest.param({"nonce": "another-nonce"}, id="other-nonce"),
        pytest.param({"exp": datetime.now(UTC) - timedelta(minutes=1)}, id="expired"),
        pytest.param({"key": OTHER_KEY}, id="not-signed-by-google"),
        pytest.param({"email": None}, id="no-email"),
    ],
)
def test_invalid_id_tokens_are_rejected(overrides: dict[str, object]):
    attempt = GoogleLoginAttempt.start(None)
    claims = {"nonce": attempt.nonce, **overrides}
    key = claims.pop("key", GOOGLE_KEY)
    assert isinstance(key, rsa.RSAPrivateKey)
    id_token = make_id_token(key=key, **claims)  # pyright: ignore[reportArgumentType]

    with pytest.raises(GoogleAuthError):
        google_client(token_endpoint_returning(id_token)).fetch_identity("auth-code", attempt)


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(400, json={"error": "invalid_grant"}), id="refused-code"),
        pytest.param(httpx.Response(200, json={"access_token": "x"}), id="no-id-token"),
        pytest.param(httpx.Response(200, text="not json"), id="not-json"),
    ],
)
def test_token_endpoint_failures_are_reported(response: httpx.Response):
    client = google_client(httpx.MockTransport(lambda request: response))

    with pytest.raises(GoogleAuthError):
        client.fetch_identity("auth-code", GoogleLoginAttempt.start(None))
