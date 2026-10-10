import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import EMAIL_MAX_LENGTH, PROVIDER_MAX_LENGTH, PROVIDER_SUBJECT_MAX_LENGTH
from app.db.base import Base


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
