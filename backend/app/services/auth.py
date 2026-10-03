"""Règles métier de l'authentification : inscription, connexion, rotation des refresh tokens.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories import refresh_tokens as refresh_token_repository
from app.repositories import users as user_repository

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_token_expires_in: int
    refresh_token: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def register(self, email: str, password: str, display_name: str) -> IssuedTokens:
        normalized_email = normalize_email(email)
        if user_repository.get_user_by_email(self._session, normalized_email) is not None:
            raise EmailAlreadyRegisteredError

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        try:
            user_repository.add_user(self._session, user)
        except IntegrityError as exc:
            # Deux inscriptions simultanées avec le même email : la contrainte d'unicité tranche
            self._session.rollback()
            raise EmailAlreadyRegisteredError from exc

        tokens = self._start_session(user, authenticated_at=datetime.now(UTC))
        self._session.commit()
        logger.info("Compte créé : user_id=%s", user.id)
        return tokens

    def login(self, email: str, password: str) -> IssuedTokens:
        user = user_repository.get_user_by_email(self._session, normalize_email(email))
        if user is None:
            verify_dummy_password(password)
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash):
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError

        tokens = self._start_session(user, authenticated_at=datetime.now(UTC))
        self._session.commit()
        return tokens

    def refresh(self, refresh_token: str) -> IssuedTokens:
        now = datetime.now(UTC)
        stored = refresh_token_repository.get_refresh_token_for_update(
            self._session, hash_refresh_token(refresh_token)
        )
        if stored is None:
            raise InvalidRefreshTokenError

        if stored.revoked_at is not None:
            # Un token déjà remplacé est rejoué : il a pu être volé. Toute la famille est
            # révoquée, ce qui déconnecte aussi celui qui détient le token le plus récent.
            refresh_token_repository.revoke_refresh_token_family(
                self._session, stored.family_id, revoked_at=now
            )
            self._session.commit()
            logger.warning(
                "Réutilisation d'un refresh token révoqué : famille %s révoquée (user_id=%s)",
                stored.family_id,
                stored.user_id,
            )
            raise InvalidRefreshTokenError

        if stored.expires_at <= now:
            raise InvalidRefreshTokenError

        stored.revoked_at = now
        user = user_repository.get_user_by_id(self._session, stored.user_id)
        if user is None:
            raise InvalidRefreshTokenError
        tokens = self._issue_tokens(
            user, family_id=stored.family_id, authenticated_at=stored.authenticated_at
        )
        self._session.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        stored = refresh_token_repository.get_refresh_token_for_update(
            self._session, hash_refresh_token(refresh_token)
        )
        if stored is None:
            return
        refresh_token_repository.revoke_refresh_token_family(
            self._session, stored.family_id, revoked_at=datetime.now(UTC)
        )
        self._session.commit()

    def get_user_from_access_token(self, access_token: str) -> User | None:
        """Utilisateur du token, ou None s'il n'existe plus. Lève InvalidAccessTokenError."""
        claims = decode_access_token(
            access_token, secret_key=self._settings.jwt_secret_key.get_secret_value()
        )
        return user_repository.get_user_by_id(self._session, claims.user_id)

    def _start_session(self, user: User, authenticated_at: datetime) -> IssuedTokens:
        return self._issue_tokens(user, family_id=uuid.uuid4(), authenticated_at=authenticated_at)

    def _issue_tokens(
        self, user: User, family_id: uuid.UUID, authenticated_at: datetime
    ) -> IssuedTokens:
        now = datetime.now(UTC)
        access_ttl = timedelta(minutes=self._settings.access_token_ttl_minutes)
        refresh_token = generate_refresh_token()
        refresh_token_repository.add_refresh_token(
            self._session,
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(refresh_token),
                family_id=family_id,
                authenticated_at=authenticated_at,
                expires_at=now + timedelta(days=self._settings.refresh_token_ttl_days),
            ),
        )
        access_token = create_access_token(
            user_id=user.id,
            auth_time=authenticated_at,
            secret_key=self._settings.jwt_secret_key.get_secret_value(),
            ttl=access_ttl,
            now=now,
        )
        return IssuedTokens(
            access_token=access_token,
            access_token_expires_in=int(access_ttl.total_seconds()),
            refresh_token=refresh_token,
        )
