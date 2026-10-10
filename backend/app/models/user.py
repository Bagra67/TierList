import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH, EMAIL_MAX_LENGTH, PASSWORD_HASH_MAX_LENGTH
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
