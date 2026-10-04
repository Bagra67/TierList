"""Primitives cryptographiques de l'authentification : mots de passe, tokens, liens par email.

Fonctions pures : la configuration (clé, durées) est passée en paramètre par le service.
"""

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
    JWT_ALGORITHM,
    PASSWORD_FINGERPRINT_LENGTH,
    PASSWORD_RESET_TOKEN_TYPE,
    REFRESH_TOKEN_BYTES,
)
from app.exceptions.auth import InvalidAccessTokenError, InvalidEmailTokenError

# Argon2id avec les paramètres recommandés par pwdlib
_password_hash = PasswordHash.recommended()
# Haché une seule fois : sert à égaliser le temps de réponse quand l'email est inconnu
_DUMMY_PASSWORD_HASH = _password_hash.hash(secrets.token_urlsafe(DUMMY_PASSWORD_BYTES))


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    # Heure de la dernière vraie connexion (mot de passe), conservée à travers les rafraîchissements
    auth_time: datetime
    # users.token_version à l'émission : le token ne vaut plus rien une fois ce compteur incrémenté
    token_version: int


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def verify_dummy_password(password: str) -> None:
    """Prend le temps d'une vraie vérification : ne révèle pas qu'un email n'existe pas."""
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
        "ver": token_version,
    }
    return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, secret_key: str) -> AccessTokenClaims:
    try:
        claims = jwt.decode(
            token,
            secret_key,
            # Liste explicite : empêche les attaques par changement d'algorithme (ex. « none »)
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "iat", "exp", "auth_time", "ver"]},
        )
        if claims["type"] != ACCESS_TOKEN_TYPE:
            raise InvalidAccessTokenError("Type de token inattendu")
        if type(claims["ver"]) is not int:
            raise InvalidAccessTokenError("Version de token invalide")
        return AccessTokenClaims(
            user_id=uuid.UUID(claims["sub"]),
            auth_time=datetime.fromtimestamp(claims["auth_time"], UTC),
            token_version=claims["ver"],
        )
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise InvalidAccessTokenError("Access token invalide") from exc


@dataclass(frozen=True)
class EmailVerificationClaims:
    user_id: uuid.UUID
    # Empreinte de l'adresse à confirmer : si l'email du compte a changé, le lien ne vaut plus rien
    email_fingerprint: str


def email_fingerprint(email: str) -> str:
    """Empreinte d'une adresse, mise dans les liens à sa place.

    Un JWT se lit sans la clé : l'adresse en clair dans un lien finirait dans les logs (proxy,
    serveur web), qui ne doivent contenir aucun email.
    """
    return hashlib.sha256(email.encode()).hexdigest()[:EMAIL_FINGERPRINT_LENGTH]


def create_email_verification_token(
    *,
    user_id: uuid.UUID,
    email: str,
    secret_key: str,
    ttl: timedelta,
    now: datetime | None = None,
) -> str:
    # Signé et non stocké : un lien utilisé deux fois confirme simplement une adresse déjà confirmée
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
        # Le type empêche de présenter un access token (même clé de signature) comme lien
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
    # Empreinte du mot de passe au moment de la demande : le lien ne sert plus une fois changé
    password_fingerprint: str


def password_fingerprint(password_hash: str | None, *, secret_key: str) -> str:
    """Empreinte du hash du mot de passe actuel (vide pour un compte sans mot de passe).

    Mise dans le lien de réinitialisation, elle change dès que le mot de passe change : le lien
    ne sert qu'une fois, sans rien stocker. HMAC avec la clé : rien n'est déductible du hash.
    """
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
    # SHA-256 suffit : le token est aléatoire (256 bits), un hachage lent n'apporterait rien.
    return hashlib.sha256(refresh_token.encode()).hexdigest()
