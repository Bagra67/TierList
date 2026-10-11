import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.user import User


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une place dans une salle, gardée malgré les déconnexions. Le room admin a la sienne dès
    la création : il compte dans la limite de participants, même s'il ne joue pas."""

    __tablename__ = "participants"
    __table_args__ = (
        # Un utilisateur a au plus une place par salle
        UniqueConstraint("room_id", "user_id"),
    )

    # Sans index propre : la contrainte d'unicité (room_id, user_id) commence par room_id et sert
    # déjà aux recherches par salle
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    # Toujours un compte pour l'instant : les invités arrivent avec #87
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    room: Mapped["Room"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()
