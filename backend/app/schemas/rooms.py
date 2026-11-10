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
    template_id: uuid.UUID


TimerSeconds = Annotated[int, Field(ge=TIMER_SECONDS_MIN, le=TIMER_SECONDS_MAX)]
CooldownSeconds = Annotated[int, Field(ge=COOLDOWN_SECONDS_MIN, le=COOLDOWN_SECONDS_MAX)]


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
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


class RoomTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    hidden: bool


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    is_admin: bool
    is_guest: bool
    connected: bool
    is_you: bool


class CurrentItemResponse(BaseModel):
    """Un item de la partie, une tuile de la version figée : l'item du tour en cours (montré à
    tous), un item placé par le lecteur, ou un item qu'il a manqué."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool


class GameTierResponse(BaseModel):
    """Un tier de la version figée de la partie, où placer les items."""

    id: uuid.UUID
    name: str
    color: str


class OwnPlacementResponse(BaseModel):
    """Un item placé par le lecteur : son tier et sa position (0 = premier). Placement de tour
    pendant les tours, placement final pendant le cooldown."""

    item: CurrentItemResponse
    tier_id: uuid.UUID
    position: int


class CurrentGameResponse(BaseModel):
    status: GameStatus
    round_number: int
    round_count: int
    current_item: CurrentItemResponse
    ends_at: datetime | None
    tiers: list[GameTierResponse]
    placed_participant_ids: list[uuid.UUID]
    own_placements: list[OwnPlacementResponse]
    cooldown_ends_at: datetime | None
    missed_items: list[CurrentItemResponse]


class PlaceItemRequest(BaseModel):
    tier_id: uuid.UUID
    position: Annotated[int, Field(ge=0)]


class RoomBanResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    is_guest: bool


class PastGameResponse(BaseModel):
    """Une partie close (parties passées d'une salle, historique d'un compte) : son lien de
    résultats (/results/<public_token>)."""

    public_token: str
    template_name: str
    closed_at: datetime
    player_count: int


class RoomResponse(BaseModel):
    code: str
    version: int
    link: str
    status: RoomStatus
    template: RoomTemplateResponse | None
    settings: RoomSettingsResponse
    participants: list[ParticipantResponse]
    is_admin: bool
    bans: list[RoomBanResponse]
    game: CurrentGameResponse | None
    past_games: list[PastGameResponse]
    server_now: datetime = Field(
        description="Heure du serveur au moment de la réponse : le client en déduit le décalage "
        "de son horloge, pour que ses minuteurs suivent ceux du serveur."
    )


class JoinAsGuestRequest(BaseModel):
    nickname: DisplayName


class RestoreGuestRequest(BaseModel):
    token: str


class GuestRoomResponse(RoomResponse):
    """Salle rejointe en invité, avec le lien perso : donné une seule fois, la base n'en gardant
    que l'empreinte."""

    guest_link: str
    guest_link_expires_at: datetime
