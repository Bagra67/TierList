import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.rooms import ROOM_CODE_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import AutoAdvance, GameStatus, ItemOrder, RoomStatus

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.participant import Participant
    from app.models.room_ban import RoomBan
    from app.models.template import Template


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Le lieu où un groupe joue, rejoint par son code ou son lien. Ses réglages sont des
    colonnes de la salle (composition 1-1 du modèle de domaine) et s'appliquent à la partie
    suivante (docs/technical/rooms.md)."""

    __tablename__ = "rooms"

    # Code court, unique, que le lien reprend
    code: Mapped[str] = mapped_column(String(ROOM_CODE_LENGTH), unique=True)
    # Le room admin : supprimer son compte supprime ses salles
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SET NULL et non CASCADE : la purge d'un template supprimé n'efface pas la salle ; sans
    # template, aucune nouvelle partie ne peut y démarrer
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[RoomStatus] = mapped_column(
        text_enum(RoomStatus, "room_status"), default=RoomStatus.OPEN
    )

    # --- Réglages ------------------------------------------------------------------------------
    item_order: Mapped[ItemOrder] = mapped_column(
        text_enum(ItemOrder, "item_order"), default=ItemOrder.TEMPLATE
    )
    auto_advance: Mapped[AutoAdvance] = mapped_column(
        text_enum(AutoAdvance, "auto_advance"), default=AutoAdvance.NONE
    )
    # Gardé même sans timer : la durée choisie est retrouvée si le timer est remis
    timer_seconds: Mapped[int]
    # Durée du cooldown final
    cooldown_seconds: Mapped[int]
    # False : le room admin a seulement les commandes, sans tier list ni place dans les résultats
    admin_plays: Mapped[bool] = mapped_column(default=True)
    # Seul réglage modifiable pendant une partie ; faux, il verrouille les arrivées (US-2.10)
    late_arrivals_allowed: Mapped[bool] = mapped_column(default=True)
    # Incrémentée dans la même transaction à chaque changement de la salle (arrivée, départ,
    # réglages, présence) : le room_version des événements temps réel. Un client qui voit un saut
    # sait qu'il a manqué un événement et relit la salle (docs/technical/realtime.md)
    version: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    template: Mapped["Template | None"] = relationship()
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan", order_by="Participant.created_at"
    )
    # Visibles du room admin seulement (US-2.12)
    bans: Mapped[list["RoomBan"]] = relationship(
        cascade="all, delete-orphan", order_by="RoomBan.created_at"
    )
    # La partie en cours, s'il y en a une (au plus une, invariant 3). Lecture seule : une partie
    # se crée par le service des parties, et la base la détache (SET NULL) quand la salle est
    # supprimée
    current_game: Mapped["Game | None"] = relationship(
        primaryjoin=f"and_(Game.room_id == Room.id, Game.status != '{GameStatus.CLOSED}')",
        viewonly=True,
        uselist=False,
    )
