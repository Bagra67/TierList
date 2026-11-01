import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountBan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Le bannissement d'un compte par un super admin (US-1.8) : temporaire (ends_at) ou définitif
    (ends_at vide), avec un motif montré à la personne quand elle tente de se connecter.

    Actif tant qu'il n'est pas levé (lifted_at vide) et que sa fin n'est pas passée : un
    bannissement temporaire finit seul. Ne pas confondre avec RoomBan, le bannissement d'une
    salle par son room admin. Gardé jusqu'à la suppression du compte : l'historique des sanctions
    sert à repérer la récidive."""

    __tablename__ = "account_bans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Le super admin qui l'a décidé ; son nom est copié, il reste lisible après la suppression
    # de son compte
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    reason: Mapped[str] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
    # Fin d'un bannissement temporaire ; None pour un bannissement définitif
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Levé par un super admin, ou remplacé par un nouveau bannissement
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
