import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.constants.auth import (
    ACCESS_TOKEN_TYPE,
    DUMMY_PASSWORD_BYTES,
    EMAIL_FINGERPRINT_LENGTH,
    EMAIL_VERIFICATION_TOKEN_TYPE,
    GOOGLE_BAN_NOTICE_TOKEN_TYPE,
    JWT_ALGORITHM,
    PASSWORD_FINGERPRINT_LENGTH,
    PASSWORD_RESET_TOKEN_TYPE,
    REFRESH_TOKEN_BYTES,
)
from app.constants.games import PUBLIC_RESULTS_TOKEN_BYTES
from app.constants.rooms import GUEST_TOKEN_BYTES
from app.exceptions.auth import (
    InvalidAccessTokenError,
    InvalidBanNoticeError,
    InvalidEmailTokenError,
)

_password_hash = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _password_hash.hash(secrets.token_urlsafe(DUMMY_PASSWORD_BYTES))


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    auth_time: datetime
    token_version: int


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def spend_password_verification_time(password: str) -> None:
    _password_hash.verify(password, _DUMMY_PASSWORD_HASH)


def create_access_token(
    *,
    user_id: uuid.UUID,
    auth_time: datetime,
    token_version: int,
    secret_key: str,
    ttl: timedelta,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + ttl,
        "auth_time": int(auth_time.timestamp()),
        "token_version": token_version,
    }
    return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, secret_key: str) -> AccessTokenClaims:
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp", "auth_time", "token_version"]},
        )
        if claims["type"] != ACCESS_TOKEN_TYPE:
            raise InvalidAccessTokenError("Type de token inattendu")
        return AccessTokenClaims(
            user_id=uuid.UUID(claims["sub"]),
            auth_time=datetime.fromtimestamp(claims["auth_time"], UTC),
            token_version=claims["token_version"],
        )
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError("Access token invalide") from exc


def create_ban_notice_token(
    *, user_id: uuid.UUID, secret_key: str, ttl: timedelta, now: datetime | None = None
) -> str:
    issued_at = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": GOOGLE_BAN_NOTICE_TOKEN_TYPE,
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)


def decode_ban_notice_token(token: str, *, secret_key: str) -> uuid.UUID:
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
        if claims["type"] != GOOGLE_BAN_NOTICE_TOKEN_TYPE:
            raise InvalidBanNoticeError("Type de token inattendu")
        return uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidBanNoticeError("Cookie du motif invalide") from exc


@dataclass(frozen=True)
class EmailVerificationClaims:
    user_id: uuid.UUID
    email_fingerprint: str


def email_fingerprint(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:EMAIL_FINGERPRINT_LENGTH]


def create_email_verification_token(
    *,
    user_id: uuid.UUID,
    email: str,
    secret_key: str,
    ttl: timedelta,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": EMAIL_VERIFICATION_TOKEN_TYPE,
        "email": email_fingerprint(email),
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)


def decode_email_verification_token(token: str, *, secret_key: str) -> EmailVerificationClaims:
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "email", "iat", "exp"]},
        )
        if claims["type"] != EMAIL_VERIFICATION_TOKEN_TYPE:
            raise InvalidEmailTokenError("Type de token inattendu")
        return EmailVerificationClaims(
            user_id=uuid.UUID(claims["sub"]), email_fingerprint=str(claims["email"])
        )
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidEmailTokenError("Lien de vérification invalide") from exc


@dataclass(frozen=True)
class PasswordResetClaims:
    user_id: uuid.UUID
    password_fingerprint: str


def password_fingerprint(password_hash: str | None, *, secret_key: str) -> str:
    digest = hmac.new(secret_key.encode(), (password_hash or "").encode(), hashlib.sha256)
    return digest.hexdigest()[:PASSWORD_FINGERPRINT_LENGTH]


def create_password_reset_token(
    *,
    user_id: uuid.UUID,
    password_fingerprint: str,
    secret_key: str,
    ttl: timedelta,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "type": PASSWORD_RESET_TOKEN_TYPE,
        "pwd": password_fingerprint,
        "iat": issued_at,
        "exp": issued_at + ttl,
    }
    return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)


def decode_password_reset_token(token: str, *, secret_key: str) -> PasswordResetClaims:
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "pwd", "iat", "exp"]},
        )
        if claims["type"] != PASSWORD_RESET_TOKEN_TYPE:
            raise InvalidEmailTokenError("Type de token inattendu")
        return PasswordResetClaims(
            user_id=uuid.UUID(claims["sub"]), password_fingerprint=str(claims["pwd"])
        )
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidEmailTokenError("Lien de réinitialisation invalide") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode()).hexdigest()


def generate_guest_token() -> str:
    return secrets.token_urlsafe(GUEST_TOKEN_BYTES)


def generate_public_results_token() -> str:
    return secrets.token_urlsafe(PUBLIC_RESULTS_TOKEN_BYTES)


def hash_guest_token(guest_token: str) -> str:
    return hashlib.sha256(guest_token.encode()).hexdigest()
