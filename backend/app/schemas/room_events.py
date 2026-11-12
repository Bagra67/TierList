import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ParticipantJoinedData(BaseModel):
    participant_id: uuid.UUID


class ParticipantJoinedEvent(BaseModel):
    """Un compte ou un invité vient d'entrer : le client relit la salle."""

    type: Literal["participant.joined"] = "participant.joined"
    room_version: int
    data: ParticipantJoinedData


class ParticipantPresenceData(BaseModel):
    participant_id: uuid.UUID
    connected: bool


class ParticipantPresenceEvent(BaseModel):
    """Un participant vient de se connecter, ou de se déconnecter (délai de grâce écoulé)."""

    type: Literal["participant.presence"] = "participant.presence"
    room_version: int
    data: ParticipantPresenceData


class ParticipantRemovedData(BaseModel):
    participant_id: uuid.UUID


class ParticipantRemovedEvent(BaseModel):
    """Le room admin a retiré ou banni un participant : sa place n'existe plus."""

    type: Literal["participant.removed"] = "participant.removed"
    room_version: int
    data: ParticipantRemovedData


class GameStartedData(BaseModel):
    """Premier tour de la partie ; `ends_at` est la fin du tour quand il a un minuteur."""

    round_number: int
    round_count: int
    ends_at: datetime | None


class GameStartedEvent(BaseModel):
    """Le room admin a lancé une partie : le premier item est montré à tous."""

    type: Literal["game.started"] = "game.started"
    room_version: int
    data: GameStartedData


class ParticipantPlacedData(BaseModel):
    """Le participant qui a placé l'item, et le tour concerné."""

    participant_id: uuid.UUID
    round_number: int


class ParticipantPlacedEvent(BaseModel):
    """Un participant a placé l'item en cours pour la première fois de ce tour."""

    type: Literal["participant.placed"] = "participant.placed"
    room_version: int
    data: ParticipantPlacedData


class RoundStartedData(BaseModel):
    """Nouveau tour ; `ends_at` est la fin du tour quand il a un minuteur."""

    round_number: int
    round_count: int
    ends_at: datetime | None


class RoundStartedEvent(BaseModel):
    """Le tour précédent est fini (« suivant », timer ou « tout le monde a placé ») : l'item
    suivant est montré à tous."""

    type: Literal["round.started"] = "round.started"
    room_version: int
    data: RoundStartedData


class CooldownStartedData(BaseModel):
    """Fin du cooldown final."""

    ends_at: datetime


class CooldownStartedEvent(BaseModel):
    """Le dernier tour est fini : le cooldown final commence (#96)."""

    type: Literal["cooldown.started"] = "cooldown.started"
    room_version: int
    data: CooldownStartedData


class GameClosedData(BaseModel):
    """La partie qui vient d'être close."""

    game_id: uuid.UUID


class GameClosedEvent(BaseModel):
    """Le cooldown final est fini (timer ou « Terminer maintenant ») : la partie est close et la
    salle redevient ouverte."""

    type: Literal["game.closed"] = "game.closed"
    room_version: int
    data: GameClosedData


class RoomSettingsUpdatedData(BaseModel):
    pass


class RoomSettingsUpdatedEvent(BaseModel):
    """Le room admin a changé les réglages : le client relit la salle."""

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
    """Battement de cœur du serveur : le client répond pong."""

    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    """Réponse du client au ping du serveur, dans le délai `ROOM_HEARTBEAT_TIMEOUT_SECONDS` (5 s
    par défaut)."""

    type: Literal["pong"] = "pong"


class AuthMessage(BaseModel):
    """Premier message du client : l'access token d'un compte, ou None pour un invité (reconnu par
    son cookie). Le token ne passe jamais dans l'URL."""

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
