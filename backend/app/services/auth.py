"""Règles métier de l'authentification : inscription, connexion, rotation des refresh tokens,
vérification de l'adresse email, réinitialisation du mot de passe.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
"""

import logging
import uuid
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
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_access_token,
    decode_email_verification_token,
    decode_password_reset_token,
    email_fingerprint,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_fingerprint,
    verify_dummy_password,
    verify_password,
)
from app.emails.templates import password_reset_email, verification_email
from app.exceptions.auth import (
    EmailAlreadyRegisteredError,
    GoogleEmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidEmailTokenError,
    InvalidRefreshTokenError,
    ReauthenticationRequiredError,
)
from app.models.user import OAuthAccount, RefreshToken, User
from app.repositories import oauth_accounts as oauth_account_repository
from app.repositories import refresh_tokens as refresh_token_repository
from app.repositories import users as user_repository
from app.services.email import Email
from app.services.google_oauth import GoogleIdentity

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class Registration:
    tokens: IssuedTokens
    # Envoyé par la route en tâche de fond, après la réponse
    verification_email: Email


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _revoke_access_tokens(user: User) -> None:
    """Refuse tous les access tokens déjà émis pour l'utilisateur (claim « token_version » dépassé).

    Ses autres appareils reçoivent une 401 et rafraîchissent leur session, si leur refresh
    token est encore valable.
    """
    user.token_version += 1


def _display_name(identity: GoogleIdentity) -> str:
    # Nom du profil Google, sinon la partie de l'email avant « @ », tronqué à la longueur maximale
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
        try:
            return self._login_with_google(identity)
        except IntegrityError:
            # Première connexion simultanée (double clic, deux onglets) : l'autre requête a
            # créé le compte ou lié l'identité entre-temps, la nouvelle tentative le retrouve.
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

        tokens = self._start_session(user, authenticated_at=now)
        self._session.commit()
        return tokens

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
            # Adresse jamais confirmée : le mot de passe a pu être posé par quelqu'un qui ne la
            # possède pas, pour attendre que la vraie propriétaire se connecte avec Google
            # (prise de contrôle préalable). Google prouve la possession de l'adresse : le
            # mot de passe et les sessions ouvertes avec lui sont supprimés.
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
        user = user_repository.get_user_by_id(self._session, stored.user_id)
        if user is not None:
            _revoke_access_tokens(user)
        self._session.commit()

    def request_email_verification(self, user: User, language: Language) -> Email | None:
        """Email de vérification à renvoyer, ou None si l'adresse est déjà confirmée ou si le
        précédent email date de moins de EMAIL_COOLDOWN_SECONDS."""
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
        """Confirme l'adresse du lien ; lève InvalidEmailTokenError si le lien ne vaut rien."""
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
        """Email de réinitialisation à envoyer, ou None si aucun compte n'a cette adresse ou si
        le précédent email date de moins de EMAIL_COOLDOWN_SECONDS.

        La route répond pareil dans tous les cas : elle ne révèle pas quelles adresses ont un
        compte. Un compte créé avec Google peut ainsi définir un mot de passe.
        """
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
        """Remplace le mot de passe et ferme toutes les sessions ; lève InvalidEmailTokenError si
        le lien est invalide, expiré ou déjà utilisé (le mot de passe a changé depuis)."""
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
        # Ouvrir le lien reçu par email prouve la possession de l'adresse
        if user.email_verified_at is None:
            user.email_verified_at = now
        # Le mot de passe a pu être volé : les sessions ouvertes avec lui sont fermées
        refresh_token_repository.revoke_user_refresh_tokens(self._session, user.id, revoked_at=now)
        _revoke_access_tokens(user)
        self._session.commit()
        logger.info("Mot de passe réinitialisé, sessions fermées : user_id=%s", user.id)

    def delete_account(self, session: AuthenticatedSession, password: str | None) -> None:
        """Supprime définitivement le compte et ses sessions, une fois l'utilisateur confirmé.

        Confirmation : le mot de passe pour un compte qui en a un, sinon une connexion récente
        (moins de RECENT_AUTHENTICATION_MAX_AGE_MINUTES) : un compte Google n'a pas de mot de
        passe à redemander.
        """
        user = session.user
        max_age = timedelta(minutes=self._settings.recent_authentication_max_age_minutes)
        if user.password_hash is not None:
            if password is None or not verify_password(password, user.password_hash):
                raise IncorrectPasswordError
        elif datetime.now(UTC) - session.auth_time > max_age:
            raise ReauthenticationRequiredError
        user_id = user.id
        user_repository.delete_user(self._session, user)
        self._session.commit()
        logger.info("Compte supprimé : user_id=%s", user_id)

    def authenticate_access_token(self, access_token: str) -> AuthenticatedSession | None:
        """Session de l'access token, ou None si l'utilisateur n'existe plus ou si le token a
        été révoqué depuis son émission (déconnexion, nouveau mot de passe…).

        Lève InvalidAccessTokenError si le token est invalide.
        """
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
        """Lien vers une page du frontend, avec le token en paramètre (liens envoyés par email)."""
        return f"{self._settings.frontend_base_url}{path}?{urlencode({TOKEN_PARAM: token})}"

    def _start_session(self, user: User, authenticated_at: datetime) -> IssuedTokens:
        # Ménage à chaque connexion, sans tâche planifiée : la table ne garde que les tokens
        # encore valables, ou révoqués mais pas expirés (utiles pour repérer une réutilisation).
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
