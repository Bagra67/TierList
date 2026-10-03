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
from app.models.user import OAuthAccount, RefreshToken, User
from app.repositories import oauth_accounts as oauth_account_repository
from app.repositories import refresh_tokens as refresh_token_repository
from app.repositories import users as user_repository
from app.services.google_oauth import GoogleIdentity

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class IncorrectPasswordError(Exception):
    pass


class GoogleEmailNotVerifiedError(Exception):
    """Google ne garantit pas que l'adresse appartient à ce compte : elle ne peut servir."""


class ReauthenticationRequiredError(Exception):
    """Compte sans mot de passe dont la dernière connexion est trop ancienne pour confirmer."""


GOOGLE_PROVIDER = "google"

# Un compte Google n'a pas de mot de passe à redemander : supprimer le compte exige alors
# une connexion Google aussi récente que ce délai.
RECENT_AUTHENTICATION_MAX_AGE = timedelta(minutes=5)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    # Heure de la connexion d'origine (claim auth_time de l'access token)
    auth_time: datetime


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_token_expires_in: int
    refresh_token: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _display_name(identity: GoogleIdentity) -> str:
    # Nom du profil Google, sinon la partie de l'email avant « @ », tronqué à 50 caractères
    name = (identity.name or "").strip() or identity.email.split("@")[0]
    return name[:50]


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
        # Compte inconnu ou créé avec Google (sans mot de passe) : même réponse, même durée
        if user is None or user.password_hash is None:
            verify_dummy_password(password)
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash):
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError

        tokens = self._start_session(user, authenticated_at=datetime.now(UTC))
        self._session.commit()
        return tokens

    def login_with_google(self, identity: GoogleIdentity) -> IssuedTokens:
        """Connecte le compte lié à cette identité Google, le lie ou le crée au besoin.

        1. identité déjà liée : connexion à son compte ;
        2. sinon, email déjà inscrit : l'identité est liée à ce compte ;
        3. sinon : un compte sans mot de passe est créé.
        Les cas 2 et 3 exigent un email vérifié par Google : sans cela, n'importe qui pourrait
        prendre le contrôle d'un compte existant, ou réserver l'adresse de quelqu'un d'autre.
        """
        user = oauth_account_repository.get_user_by_oauth_account(
            self._session, GOOGLE_PROVIDER, identity.subject
        )
        if user is None:
            if not identity.email_verified:
                raise GoogleEmailNotVerifiedError
            user = self._link_google_identity(identity)

        tokens = self._start_session(user, authenticated_at=datetime.now(UTC))
        self._session.commit()
        return tokens

    def _link_google_identity(self, identity: GoogleIdentity) -> User:
        email = normalize_email(identity.email)
        user = user_repository.get_user_by_email(self._session, email)
        if user is None:
            user = User(email=email, password_hash=None, display_name=_display_name(identity))
            user_repository.add_user(self._session, user)
            logger.info("Compte créé avec Google : user_id=%s", user.id)
        else:
            logger.info("Identité Google liée à un compte existant : user_id=%s", user.id)
        oauth_account_repository.add_oauth_account(
            self._session,
            OAuthAccount(
                user_id=user.id,
                provider=GOOGLE_PROVIDER,
                provider_subject=identity.subject,
                email=email,
            ),
        )
        return user

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

    def delete_account(self, session: AuthenticatedSession, password: str | None) -> None:
        """Supprime définitivement le compte et ses sessions, une fois l'utilisateur confirmé.

        Confirmation : le mot de passe pour un compte qui en a un, sinon une connexion récente.
        """
        user = session.user
        if user.password_hash is not None:
            if password is None or not verify_password(password, user.password_hash):
                raise IncorrectPasswordError
        elif datetime.now(UTC) - session.auth_time > RECENT_AUTHENTICATION_MAX_AGE:
            raise ReauthenticationRequiredError
        user_id = user.id
        user_repository.delete_user(self._session, user)
        self._session.commit()
        logger.info("Compte supprimé : user_id=%s", user_id)

    def authenticate_access_token(self, access_token: str) -> AuthenticatedSession | None:
        """Session de l'access token, ou None si l'utilisateur n'existe plus.

        Lève InvalidAccessTokenError si le token est invalide.
        """
        claims = decode_access_token(
            access_token, secret_key=self._settings.jwt_secret_key.get_secret_value()
        )
        user = user_repository.get_user_by_id(self._session, claims.user_id)
        if user is None:
            return None
        return AuthenticatedSession(user=user, auth_time=claims.auth_time)

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
