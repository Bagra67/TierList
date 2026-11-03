import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.auth import (
    DISPLAY_NAME_MAX_LENGTH,
    FRONTEND_RESET_PASSWORD,
    FRONTEND_VERIFY_EMAIL,
    GOOGLE_PROVIDER,
    TOKEN_PARAM,
)
from app.constants.i18n import Language
from app.core.config import Settings
from app.core.email_addresses import normalize_email
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_access_token,
    decode_ban_notice_token,
    decode_email_verification_token,
    decode_password_reset_token,
    email_fingerprint,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_fingerprint,
    spend_password_verification_time,
    verify_password,
)
from app.emails.templates import password_reset_email, verification_email
from app.exceptions.auth import (
    AccountBannedError,
    EmailAlreadyRegisteredError,
    GoogleEmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidEmailTokenError,
    InvalidRefreshTokenError,
    ReauthenticationRequiredError,
)
from app.models.account_ban import AccountBan
from app.models.oauth_account import OAuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories import account_bans as account_ban_repository
from app.repositories import oauth_accounts as oauth_account_repository
from app.repositories import refresh_tokens as refresh_token_repository
from app.repositories import users as user_repository
from app.services.email import Email
from app.services.google_oauth import GoogleIdentity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    auth_time: datetime


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_token_expires_in: int
    refresh_token: str


@dataclass(frozen=True)
class Registration:
    tokens: IssuedTokens
    verification_email: Email


def _revoke_access_tokens(user: User) -> None:
    user.token_version += 1


def _display_name(identity: GoogleIdentity) -> str:
    name = (identity.name or "").strip() or identity.email.split("@")[0]
    return name[:DISPLAY_NAME_MAX_LENGTH]


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def register(
        self, email: str, password: str, display_name: str, language: Language
    ) -> Registration:
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

        now = datetime.now(UTC)
        tokens = self._start_session(user, authenticated_at=now)
        email_to_send = self._verification_email(user, language, now)
        self._session.commit()
        logger.info("Compte créé : user_id=%s", user.id)
        return Registration(tokens=tokens, verification_email=email_to_send)

    def login(self, email: str, password: str) -> IssuedTokens:
        user = user_repository.get_user_by_email(self._session, normalize_email(email))
        if user is None or user.password_hash is None:
            spend_password_verification_time(password)
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash):
            logger.info("Échec de connexion : identifiants invalides")
            raise InvalidCredentialsError
        self._check_not_banned(user.id)

        tokens = self._start_session(user, authenticated_at=datetime.now(UTC))
        self._session.commit()
        return tokens

    def login_with_google(self, identity: GoogleIdentity) -> IssuedTokens:
        try:
            return self._login_with_google(identity)
        except IntegrityError:
            self._session.rollback()
            logger.info("Connexion Google simultanée, nouvelle tentative")
            return self._login_with_google(identity)

    def _login_with_google(self, identity: GoogleIdentity) -> IssuedTokens:
        user = oauth_account_repository.get_user_by_oauth_account(
            self._session, GOOGLE_PROVIDER, identity.subject
        )
        now = datetime.now(UTC)
        if user is None:
            if not identity.email_verified:
                raise GoogleEmailNotVerifiedError
            user = self._link_google_identity(identity, now)
        self._check_not_banned(user.id)

        tokens = self._start_session(user, authenticated_at=now)
        self._session.commit()
        return tokens

    def check_ban_notice(self, token: str) -> None:
        user_id: uuid.UUID = decode_ban_notice_token(
            token, secret_key=self._settings.jwt_secret_key.get_secret_value()
        )
        self._check_not_banned(user_id)

    def _check_not_banned(self, user_id: uuid.UUID) -> None:
        ban: AccountBan | None = account_ban_repository.get_active_ban(
            self._session, user_id, datetime.now(UTC)
        )
        if ban is not None:
            logger.info("Connexion refusée : compte banni, user_id=%s", user_id)
            raise AccountBannedError(user_id, ban.reason, ban.ends_at)

    def _link_google_identity(self, identity: GoogleIdentity, now: datetime) -> User:
        email = normalize_email(identity.email)
        user = user_repository.get_user_by_email(self._session, email)
        if user is None:
            user = User(
                email=email,
                password_hash=None,
                display_name=_display_name(identity),
                email_verified_at=now,
            )
            user_repository.add_user(self._session, user)
            logger.info("Compte créé avec Google : user_id=%s", user.id)
        elif user.email_verified_at is None:
            user.password_hash = None
            user.email_verified_at = now
            refresh_token_repository.revoke_user_refresh_tokens(
                self._session, user.id, revoked_at=now
            )
            _revoke_access_tokens(user)
            logger.info(
                "Identité Google liée à un compte non vérifié, mot de passe retiré : user_id=%s",
                user.id,
            )
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
        if account_ban_repository.get_active_ban(self._session, user.id, now) is not None:
            refresh_token_repository.revoke_refresh_token_family(
                self._session, stored.family_id, revoked_at=now
            )
            self._session.commit()
            logger.info("Rafraîchissement refusé : compte banni, user_id=%s", user.id)
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
        user = user_repository.get_user_by_id(self._session, stored.user_id)
        if user is not None:
            _revoke_access_tokens(user)
        self._session.commit()

    def request_email_verification(self, user: User, language: Language) -> Email | None:
        if user.email_verified_at is not None:
            return None
        now = datetime.now(UTC)
        cooldown = timedelta(seconds=self._settings.email_cooldown_seconds)
        sent_at = user.verification_email_sent_at
        if sent_at is not None and now - sent_at < cooldown:
            logger.info("Email de vérification non renvoyé, trop rapproché : user_id=%s", user.id)
            return None
        email_to_send = self._verification_email(user, language, now)
        self._session.commit()
        return email_to_send

    def verify_email(self, token: str) -> None:
        claims = decode_email_verification_token(
            token, secret_key=self._settings.jwt_secret_key.get_secret_value()
        )
        user = user_repository.get_user_by_id(self._session, claims.user_id)
        if user is None or email_fingerprint(user.email) != claims.email_fingerprint:
            raise InvalidEmailTokenError("Le lien ne correspond plus au compte")
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
            self._session.commit()
            logger.info("Adresse email confirmée : user_id=%s", user.id)

    def request_password_reset(self, email: str, language: Language) -> Email | None:
        user = user_repository.get_user_by_email(self._session, normalize_email(email))
        if user is None:
            return None
        now = datetime.now(UTC)
        cooldown = timedelta(seconds=self._settings.email_cooldown_seconds)
        sent_at = user.password_reset_email_sent_at
        if sent_at is not None and now - sent_at < cooldown:
            logger.info(
                "Email de réinitialisation non renvoyé, trop rapproché : user_id=%s", user.id
            )
            return None

        ttl_minutes = self._settings.password_reset_ttl_minutes
        secret_key = self._settings.jwt_secret_key.get_secret_value()
        token = create_password_reset_token(
            user_id=user.id,
            password_fingerprint=password_fingerprint(user.password_hash, secret_key=secret_key),
            secret_key=secret_key,
            ttl=timedelta(minutes=ttl_minutes),
            now=now,
        )
        user.password_reset_email_sent_at = now
        self._session.commit()
        logger.info("Email de réinitialisation du mot de passe demandé : user_id=%s", user.id)
        return password_reset_email(
            language,
            to=user.email,
            display_name=user.display_name,
            link=self._frontend_link(FRONTEND_RESET_PASSWORD, token),
            ttl_minutes=ttl_minutes,
        )

    def reset_password(self, token: str, password: str) -> None:
        secret_key = self._settings.jwt_secret_key.get_secret_value()
        claims = decode_password_reset_token(token, secret_key=secret_key)
        user = user_repository.get_user_by_id(self._session, claims.user_id)
        if user is None or (
            password_fingerprint(user.password_hash, secret_key=secret_key)
            != claims.password_fingerprint
        ):
            raise InvalidEmailTokenError("Le lien ne correspond plus au compte")

        now = datetime.now(UTC)
        user.password_hash = hash_password(password)
        if user.email_verified_at is None:
            user.email_verified_at = now
        refresh_token_repository.revoke_user_refresh_tokens(self._session, user.id, revoked_at=now)
        _revoke_access_tokens(user)
        self._session.commit()
        logger.info("Mot de passe réinitialisé, sessions fermées : user_id=%s", user.id)

    def delete_account(
        self,
        session: AuthenticatedSession,
        password: str | None,
        before_delete: Callable[[User], None] | None = None,
    ) -> None:
        user = session.user
        max_age = timedelta(minutes=self._settings.recent_authentication_max_age_minutes)
        if user.password_hash is not None:
            if password is None or not verify_password(password, user.password_hash):
                raise IncorrectPasswordError
        elif datetime.now(UTC) - session.auth_time > max_age:
            raise ReauthenticationRequiredError
        if before_delete is not None:
            before_delete(user)
        user_id = user.id
        user_repository.delete_user(self._session, user)
        self._session.commit()
        logger.info("Compte supprimé : user_id=%s", user_id)

    def authenticate_access_token(self, access_token: str) -> AuthenticatedSession | None:
        claims = decode_access_token(
            access_token, secret_key=self._settings.jwt_secret_key.get_secret_value()
        )
        user = user_repository.get_user_by_id(self._session, claims.user_id)
        if user is None or claims.token_version != user.token_version:
            return None
        return AuthenticatedSession(user=user, auth_time=claims.auth_time)

    def _verification_email(self, user: User, language: Language, now: datetime) -> Email:
        ttl_hours = self._settings.email_verification_ttl_hours
        token = create_email_verification_token(
            user_id=user.id,
            email=user.email,
            secret_key=self._settings.jwt_secret_key.get_secret_value(),
            ttl=timedelta(hours=ttl_hours),
            now=now,
        )
        user.verification_email_sent_at = now
        return verification_email(
            language,
            to=user.email,
            display_name=user.display_name,
            link=self._frontend_link(FRONTEND_VERIFY_EMAIL, token),
            ttl_hours=ttl_hours,
        )

    def _frontend_link(self, path: str, token: str) -> str:
        return f"{self._settings.frontend_base_url}{path}?{urlencode({TOKEN_PARAM: token})}"

    def _start_session(self, user: User, authenticated_at: datetime) -> IssuedTokens:
        refresh_token_repository.delete_expired_user_refresh_tokens(
            self._session, user.id, now=authenticated_at
        )
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
            token_version=user.token_version,
            secret_key=self._settings.jwt_secret_key.get_secret_value(),
            ttl=access_ttl,
            now=now,
        )
        return IssuedTokens(
            access_token=access_token,
            access_token_expires_in=int(access_ttl.total_seconds()),
            refresh_token=refresh_token,
        )
