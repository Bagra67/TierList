import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.rooms import GUEST_TOKEN_HASH_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RoomBan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une personne bannie d'une salle par son room admin (US-2.12) : un compte, ou le navigateur
    d'un invité, reconnu par l'empreinte du jeton de son cookie. Le bannissement d'un invité est
    donc contournable (fenêtre privée, cookies effacés) : docs/technical/rooms.md."""

    __tablename__ = "room_bans"
    __table_args__ = (
        # Un compte est banni au plus une fois par salle
        UniqueConstraint("room_id", "user_id"),
        # Soit un compte, soit le navigateur d'un invité
        CheckConstraint(
            "(user_id IS NULL) = (guest_token_hash IS NOT NULL)", name="account_or_guest"
        ),
    )

    # Sans index propre : la contrainte d'unicité (room_id, user_id) commence par room_id
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    # None pour un invité ; supprimer le compte supprime ses bannissements
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Empreinte du jeton du cookie de l'invité banni (celle qu'avait sa place)
    guest_token_hash: Mapped[str | None] = mapped_column(
        String(GUEST_TOKEN_HASH_LENGTH), unique=True
    )
    # Nom au moment du bannissement, pour la liste du room admin (un invité n'en a pas d'autre)
    display_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))

    @property
    def is_guest(self) -> bool:
        return self.user_id is None
