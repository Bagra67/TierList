import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import (
    DISPLAY_NAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    PASSWORD_HASH_MAX_LENGTH,
    PROVIDER_MAX_LENGTH,
    PROVIDER_SUBJECT_MAX_LENGTH,
    REFRESH_TOKEN_HASH_LENGTH,
)
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Toujours enregistré en minuscules (normalisé par le service) : l'unicité ignore la casse
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True)
    # None pour un compte créé avec Google, qui n'a pas de mot de passe
    password_hash: Mapped[str | None] = mapped_column(String(PASSWORD_HASH_MAX_LENGTH))
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    # Heure de la confirmation de l'adresse (lien reçu par email, ou compte Google) ; None sinon
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Dernier email de vérification envoyé : limite la fréquence des renvois
    verification_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Dernier email de réinitialisation du mot de passe envoyé : limite la fréquence des envois
    password_reset_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Copié dans chaque access token (claim « token_version ») ; l'incrémenter refuse tous les
    # access tokens déjà émis (déconnexion, nouveau mot de passe…)
    token_version: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class RefreshToken(Base):
    """Refresh token émis à un utilisateur ; seul son hash SHA-256 est stocké.

    Les tokens issus d'une même connexion forment une famille (family_id) : à chaque
    rafraîchissement, le token utilisé est révoqué et remplacé par un nouveau de la famille.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(REFRESH_TOKEN_HASH_LENGTH), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Heure de la connexion d'origine, conservée par toute la famille
    authenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OAuthAccount(Base):
    """Identité externe (ex. compte Google) rattachée à un utilisateur."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(PROVIDER_MAX_LENGTH))
    # Identifiant stable du compte chez le fournisseur (claim « sub ») ; l'email peut changer
    provider_subject: Mapped[str] = mapped_column(String(PROVIDER_SUBJECT_MAX_LENGTH))
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
