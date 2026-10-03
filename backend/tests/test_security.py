import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    JWT_ALGORITHM,
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

SECRET_KEY = "unit-test-secret-key-of-at-least-32-chars"
OTHER_SECRET_KEY = "another-unit-test-secret-key-32-chars-min"


def make_token(**overrides: object) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "auth_time": int(now.timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET_KEY, algorithm=JWT_ALGORITHM)


def test_password_hash_verifies_only_the_original_password():
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_access_token_round_trip():
    user_id = uuid.uuid4()
    auth_time = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    token = create_access_token(
        user_id=user_id, auth_time=auth_time, secret_key=SECRET_KEY, ttl=timedelta(minutes=15)
    )
    claims = decode_access_token(token, secret_key=SECRET_KEY)

    assert claims.user_id == user_id
    assert claims.auth_time == auth_time


def test_expired_access_token_is_rejected():
    token = create_access_token(
        user_id=uuid.uuid4(),
        auth_time=datetime.now(UTC),
        secret_key=SECRET_KEY,
        ttl=timedelta(minutes=15),
        now=datetime.now(UTC) - timedelta(hours=1),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key=SECRET_KEY)


def test_access_token_signed_with_another_key_is_rejected():
    token = create_access_token(
        user_id=uuid.uuid4(),
        auth_time=datetime.now(UTC),
        secret_key=OTHER_SECRET_KEY,
        ttl=timedelta(minutes=15),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key=SECRET_KEY)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(make_token(type="refresh"), id="wrong-type"),
        pytest.param(make_token(sub="not-a-uuid"), id="invalid-subject"),
        pytest.param(
            jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, SECRET_KEY), id="no-expiry"
        ),
        pytest.param("not-a-jwt", id="malformed"),
    ],
)
def test_invalid_access_tokens_are_rejected(token: str):
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key=SECRET_KEY)


def test_unsigned_access_token_is_rejected():
    # Attaque classique : un token « alg: none » sans signature
    token = jwt.encode({"sub": str(uuid.uuid4()), "type": "access"}, key=None, algorithm="none")

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, secret_key=SECRET_KEY)


def test_refresh_tokens_are_random_and_hashed_deterministically():
    first, second = generate_refresh_token(), generate_refresh_token()

    assert first != second
    assert hash_refresh_token(first) == hash_refresh_token(first)
    assert hash_refresh_token(first) != first
    assert len(hash_refresh_token(first)) == 64
