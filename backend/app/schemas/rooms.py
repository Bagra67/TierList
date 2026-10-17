import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.constants.rooms import (
    COOLDOWN_SECONDS_MAX,
    COOLDOWN_SECONDS_MIN,
    TIMER_SECONDS_MAX,
    TIMER_SECONDS_MIN,
)
from app.models.enums import AutoAdvance, GameStatus, ItemOrder, RoomStatus
from app.schemas.common import DisplayName


class CreateRoomRequest(BaseModel):
    # Un template du créateur, avec au moins une tuile
    template_id: uuid.UUID


# Bornes renvoyées en params de la 422 (ge, le) : le frontend les affiche sans les recopier
TimerSeconds = Annotated[int, Field(ge=TIMER_SECONDS_MIN, le=TIMER_SECONDS_MAX)]
CooldownSeconds = Annotated[int, Field(ge=COOLDOWN_SECONDS_MIN, le=COOLDOWN_SECONDS_MAX)]


# Réglages à changer : ceux qui sont absents (ou null) restent tels quels
class UpdateRoomSettingsRequest(BaseModel):
    item_order: ItemOrder | None = None
    auto_advance: AutoAdvance | None = None
    timer_seconds: TimerSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    admin_plays: bool | None = None
    late_arrivals_allowed: bool | None = None


class RoomSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_order: ItemOrder
    auto_advance: AutoAdvance
    # Durée du timer par item, même quand auto_advance n'est pas timer
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


class RoomTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    # Nom du compte, ou pseudo de l'invité
    display_name: str
    is_admin: bool
    is_guest: bool
    # Un onglet au moins a son canal temps réel ouvert (docs/technical/realtime.md)
    connected: bool
    # La place du lecteur lui-même (« vous »)
    is_you: bool


class CurrentItemResponse(BaseModel):
    """L'item du tour en cours, montré à tous : une tuile de la version figée."""

    id: uuid.UUID
    text: str | None
    image_url: str | None


class GameTierResponse(BaseModel):
    """Un tier de la version figée de la partie, où placer les items."""

    id: uuid.UUID
    name: str
    # Format #RRGGBB
    color: str


class OwnPlacementResponse(BaseModel):
    """Un item que le lecteur a placé pendant son tour : son tier et sa position (0 = premier)."""

    item: CurrentItemResponse
    tier_id: uuid.UUID
    position: int


class CurrentGameResponse(BaseModel):
    # in_round pendant les tours, cooldown après le dernier tour
    status: GameStatus
    # Numéro du tour en cours (à partir de 1) et nombre de tours, un par tuile
    round_number: int
    round_count: int
    current_item: CurrentItemResponse
    # Fin du timer du tour, si la salle en a un ; le client affiche le compte à rebours
    ends_at: datetime | None
    # Tiers de la version figée, de haut en bas
    tiers: list[GameTierResponse]
    # Qui a placé l'item en cours, jamais où (plateau privé)
    placed_participant_ids: list[uuid.UUID]
    # Placements du lecteur seulement, par tier puis position ; jamais ceux des autres
    own_placements: list[OwnPlacementResponse]
    # Fin du cooldown final, une fois le dernier tour fini
    cooldown_ends_at: datetime | None


class PlaceItemRequest(BaseModel):
    # Un tier de la version figée de la partie
    tier_id: uuid.UUID
    # Rang voulu dans le tier, 0 = premier ; au-delà de la fin, l'item va en dernier
    position: Annotated[int, Field(ge=0)]


class RoomBanResponse(BaseModel):
    id: uuid.UUID
    # Nom au moment du bannissement
    display_name: str
    is_guest: bool


class RoomResponse(BaseModel):
    code: str
    # Version de la salle, celle des événements temps réel (room_version)
    version: int
    # Lien à partager, vers la page de la salle
    link: str
    status: RoomStatus
    # None une fois le template purgé : aucune nouvelle partie ne peut démarrer
    template: RoomTemplateResponse | None
    settings: RoomSettingsResponse
    # Dans l'ordre d'arrivée, le room admin d'abord
    participants: list[ParticipantResponse]
    # L'utilisateur qui fait la requête est-il le room admin (il peut changer les réglages)
    is_admin: bool
    # Personnes bannies de la salle, du plus ancien au plus récent : vide sauf pour le room admin
    bans: list[RoomBanResponse]
    # La partie en cours, None hors partie
    game: CurrentGameResponse | None


class JoinAsGuestRequest(BaseModel):
    # Mêmes règles que le nom affiché d'un compte ; l'unicité dans la salle est vérifiée par le
    # service
    nickname: DisplayName


class RestoreGuestRequest(BaseModel):
    # Jeton du lien perso (fragment #guest=<jeton>, lu par le frontend)
    token: str


class GuestRoomResponse(RoomResponse):
    """Salle rejointe en invité, avec le lien perso : donné une seule fois, la base n'en gardant
    que l'empreinte."""

    guest_link: str
    guest_link_expires_at: datetime
