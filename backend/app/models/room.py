import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.rooms import ROOM_CODE_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.participant import Participant
    from app.models.room_ban import RoomBan
    from app.models.template import Template


class RoomStatus(StrEnum):
    """Une salle fermée n'est pas gardée (docs/product/milestone-1/lifecycles.md) : elle est
    supprimée, il n'y a donc pas de statut « fermée »."""

    OPEN = "open"
    # Une partie est en cours : les réglages sont bloqués, sauf les arrivées
    PLAYING = "playing"


class ItemOrder(StrEnum):
    """Ordre de passage des tuiles pendant une partie."""

    TEMPLATE = "template"
    RANDOM = "random"


class AutoAdvance(StrEnum):
    """Passage automatique à l'item suivant."""

    # Le room admin passe à l'item suivant lui-même
    NONE = "none"
    # À la fin du timer de l'item (timer_seconds)
    TIMER = "timer"
    # Quand tous les joueurs ont placé l'item
    EVERYONE_PLACED = "everyone_placed"


def _text_enum(enum_class: type[StrEnum], name: str) -> Enum:
    """Colonne texte avec une contrainte CHECK plutôt qu'un type ENUM PostgreSQL : ajouter une
    valeur ne demande pas d'ALTER TYPE (même choix que Image.status)."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )


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
        _text_enum(RoomStatus, "room_status"), default=RoomStatus.OPEN
    )

    # --- Réglages ------------------------------------------------------------------------------
    item_order: Mapped[ItemOrder] = mapped_column(
        _text_enum(ItemOrder, "item_order"), default=ItemOrder.TEMPLATE
    )
    auto_advance: Mapped[AutoAdvance] = mapped_column(
        _text_enum(AutoAdvance, "auto_advance"), default=AutoAdvance.NONE
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
