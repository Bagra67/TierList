import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.rooms import GUEST_TOKEN_HASH_LENGTH, NICKNAME_INDEX
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.user import User


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une place dans une salle, gardée malgré les déconnexions : celle d'un compte (joueur ou
    room admin) ou celle d'un invité, qui n'est jamais liée à un compte. Le room admin a la
    sienne dès la création : il compte dans la limite de participants, même s'il ne joue pas."""

    __tablename__ = "participants"
    __table_args__ = (
        # Un utilisateur a au plus une place par salle (les invités, sans compte, n'y sont pas)
        UniqueConstraint("room_id", "user_id"),
        # Soit un compte, soit un invité avec son pseudo, l'empreinte de son jeton et sa date
        # d'expiration : jamais un mélange des deux
        CheckConstraint(
            "(user_id IS NULL) = (nickname IS NOT NULL)"
            " AND (nickname IS NULL) = (guest_token_hash IS NULL)"
            " AND (nickname IS NULL) = (guest_expires_at IS NULL)",
            name="account_or_guest",
        ),
        # Un pseudo d'invité est unique dans la salle, sans tenir compte de la casse. Le service
        # vérifie aussi les noms des comptes ; cet index est le dernier filet entre invités.
        Index(
            NICKNAME_INDEX,
            "room_id",
            func.lower(text("nickname")),
            unique=True,
            postgresql_where=text("nickname IS NOT NULL"),
        ),
    )

    # Sans index propre : la contrainte d'unicité (room_id, user_id) commence par room_id et sert
    # déjà aux recherches par salle
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    # None pour un invité
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # --- Invité seulement ----------------------------------------------------------------------
    nickname: Mapped[str | None] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    # Empreinte SHA-256 du jeton porté par le cookie et le lien perso (jamais le jeton lui-même)
    guest_token_hash: Mapped[str | None] = mapped_column(
        String(GUEST_TOKEN_HASH_LENGTH), unique=True
    )
    # Fin de validité du lien perso : la place est alors perdue (état « Left »)
    guest_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Présence : un onglet au moins a son canal temps réel ouvert. Écrit seulement quand il
    # change (connexion, fin du délai de grâce), pas à chaque battement de cœur
    connected: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    room: Mapped["Room"] = relationship(back_populates="participants")
    user: Mapped["User | None"] = relationship()

    @property
    def is_guest(self) -> bool:
        return self.user_id is None

    @property
    def display_name(self) -> str:
        """Nom montré aux autres : celui du compte, ou le pseudo de l'invité."""
        if self.user is not None:
            return self.user.display_name
        if self.nickname is None:
            raise RuntimeError("A participant is either an account or a guest")
        return self.nickname

    def has_expired(self, now: datetime) -> bool:
        """Place d'invité dont le lien perso a expiré ; une place de compte n'expire jamais."""
        return self.guest_expires_at is not None and self.guest_expires_at <= now
