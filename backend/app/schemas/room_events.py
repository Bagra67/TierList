import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ParticipantJoinedData(BaseModel):
    participant_id: uuid.UUID


class ParticipantJoinedEvent(BaseModel):
    """An account or a guest just came in: the client reads the room again."""

    type: Literal["participant.joined"] = "participant.joined"
    room_version: int
    data: ParticipantJoinedData


class ParticipantPresenceData(BaseModel):
    participant_id: uuid.UUID
    connected: bool


class ParticipantPresenceEvent(BaseModel):
    """A participant just connected, or disconnected (grace period over)."""

    type: Literal["participant.presence"] = "participant.presence"
    room_version: int
    data: ParticipantPresenceData


class ParticipantRemovedData(BaseModel):
    participant_id: uuid.UUID


class ParticipantRemovedEvent(BaseModel):
    """The room admin removed or banned a participant: their place no longer exists."""

    type: Literal["participant.removed"] = "participant.removed"
    room_version: int
    data: ParticipantRemovedData


class GameStartedData(BaseModel):
    """First round of the game; `ends_at` is the end of the round when it has a timer."""

    round_number: int
    round_count: int
    ends_at: datetime | None


class GameStartedEvent(BaseModel):
    """The room admin started a game: the first item is shown to everyone."""

    type: Literal["game.started"] = "game.started"
    room_version: int
    data: GameStartedData


class ParticipantPlacedData(BaseModel):
    """The participant who placed the item, and the round concerned."""

    participant_id: uuid.UUID
    round_number: int


class ParticipantPlacedEvent(BaseModel):
    """A participant placed the current item for the first time in this round."""

    type: Literal["participant.placed"] = "participant.placed"
    room_version: int
    data: ParticipantPlacedData


class RoundStartedData(BaseModel):
    """New round; `ends_at` is the end of the round when it has a timer."""

    round_number: int
    round_count: int
    ends_at: datetime | None


class RoundStartedEvent(BaseModel):
    """The previous round is over ("next", timer or "everyone placed"): the next item is shown to
    everyone."""

    type: Literal["round.started"] = "round.started"
    room_version: int
    data: RoundStartedData


class CooldownStartedData(BaseModel):
    """End of the final cooldown."""

    ends_at: datetime


class CooldownStartedEvent(BaseModel):
    """The last round is over: the final cooldown starts (#96)."""

    type: Literal["cooldown.started"] = "cooldown.started"
    room_version: int
    data: CooldownStartedData


class GameClosedData(BaseModel):
    """The game that was just closed."""

    game_id: uuid.UUID


class GameClosedEvent(BaseModel):
    """The final cooldown is over (timer or "Finish now"): the game is closed and the room is open
    again."""

    type: Literal["game.closed"] = "game.closed"
    room_version: int
    data: GameClosedData


class RoomSettingsUpdatedData(BaseModel):
    pass


class RoomSettingsUpdatedEvent(BaseModel):
    """The room admin changed the settings: the client reads the room again."""

    type: Literal["room.settings_updated"] = "room.settings_updated"
    room_version: int
    data: RoomSettingsUpdatedData = Field(default_factory=RoomSettingsUpdatedData)


RoomEvent = Annotated[
    ParticipantJoinedEvent
    | ParticipantPresenceEvent
    | ParticipantRemovedEvent
    | RoomSettingsUpdatedEvent
    | GameStartedEvent
    | ParticipantPlacedEvent
    | RoundStartedEvent
    | CooldownStartedEvent
    | GameClosedEvent,
    Field(discriminator="type"),
]


class PingMessage(BaseModel):
    """Server heartbeat: the client answers pong."""

    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    """Client reply to the server ping, within `ROOM_HEARTBEAT_TIMEOUT_SECONDS` (5 s by default)."""

    type: Literal["pong"] = "pong"


class AuthMessage(BaseModel):
    """First message of the client: the access token of an account, or None for a guest (recognized
    by their cookie). The token never goes in the URL."""

    type: Literal["auth"] = "auth"
    access_token: str | None = None


RoomServerMessage = Annotated[
    ParticipantJoinedEvent
    | ParticipantPresenceEvent
    | ParticipantRemovedEvent
    | RoomSettingsUpdatedEvent
    | GameStartedEvent
    | ParticipantPlacedEvent
    | RoundStartedEvent
    | CooldownStartedEvent
    | GameClosedEvent
    | PingMessage,
    Field(discriminator="type"),
]
RoomClientMessage = Annotated[AuthMessage | PongMessage, Field(discriminator="type")]
