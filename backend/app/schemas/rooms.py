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
    """Template of the new room."""

    template_id: uuid.UUID


TimerSeconds = Annotated[int, Field(ge=TIMER_SECONDS_MIN, le=TIMER_SECONDS_MAX)]
CooldownSeconds = Annotated[int, Field(ge=COOLDOWN_SECONDS_MIN, le=COOLDOWN_SECONDS_MAX)]


class UpdateRoomSettingsRequest(BaseModel):
    """Changes to the room settings: only the fields sent change; a request without a field changes
    nothing."""

    item_order: ItemOrder | None = None
    auto_advance: AutoAdvance | None = None
    timer_seconds: TimerSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    admin_plays: bool | None = None
    late_arrivals_allowed: bool | None = None


class RoomSettingsResponse(BaseModel):
    """Room settings: those of the current game during a game, otherwise those of the next one.
    `timer_seconds` is kept even when `auto_advance` is not `timer`."""

    model_config = ConfigDict(from_attributes=True)

    item_order: ItemOrder
    auto_advance: AutoAdvance
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


class RoomTemplateResponse(BaseModel):
    """Template of the room; `hidden` is true when moderation hid it: no new game can start then."""

    id: uuid.UUID
    name: str
    hidden: bool


class ParticipantResponse(BaseModel):
    """A place in the room: an account with its display name, or a guest with their nickname.
    `is_you` marks the reader's place."""

    id: uuid.UUID
    display_name: str
    is_admin: bool
    is_guest: bool
    connected: bool
    is_you: bool


class CurrentItemResponse(BaseModel):
    """An item of the game, a tile of the frozen version: the item of the current round (shown to
    everyone), an item placed by the reader, or an item they missed."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool


class GameTierResponse(BaseModel):
    """A tier of the frozen version of the game, where items are placed."""

    id: uuid.UUID
    name: str
    color: str


class OwnPlacementResponse(BaseModel):
    """An item placed by the reader: its tier and its position (0 = first). Round placement during
    the rounds, final placement during the cooldown."""

    item: CurrentItemResponse
    tier_id: uuid.UUID
    position: int


class CurrentGameResponse(BaseModel):
    """The current game, as the reader sees it: only their own placements are sent, with the list of
    those who placed the item of the round. `ends_at` is the end of the round when it has a timer;
    `cooldown_ends_at` and `missed_items` are used during the final cooldown."""

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
    """Tier chosen for the item, and position in that tier (0 = first); a position past the end puts
    the item last."""

    tier_id: uuid.UUID
    position: Annotated[int, Field(ge=0)]


class RoomBanResponse(BaseModel):
    """A ban from the room, visible to the admin only."""

    id: uuid.UUID
    display_name: str
    is_guest: bool


class PastGameResponse(BaseModel):
    """A closed game (past games of a room, history of an account): its results link
    (/results/<public_token>)."""

    public_token: str
    template_name: str
    closed_at: datetime
    player_count: int


class RoomResponse(BaseModel):
    """A room as a participant sees it. `version` increases with every change to the room; `bans` is
    only filled for the admin; `template` is null when the template was purged; `game` is null
    outside a game."""

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
        description="Server time when the response was made: the client derives the offset of "
        "its clock from it, so its timers follow the server ones."
    )


class JoinAsGuestRequest(BaseModel):
    """Nickname of the guest in the room."""

    nickname: DisplayName


class RestoreGuestRequest(BaseModel):
    """Token of the guest's personal link."""

    token: str


class GuestRoomResponse(RoomResponse):
    """Room joined as a guest, with the personal link: given only once, since the database only
    keeps its hash."""

    guest_link: str
    guest_link_expires_at: datetime
