"""Messages du canal temps réel d'une salle (docs/technical/realtime.md).

Le serveur pousse des événements ({type, room_version, data}) ; le client n'envoie que son
message d'authentification et la réponse au battement de cœur. Ces modèles sont ajoutés au
schéma OpenAPI (app/main.py) pour que le frontend en génère les types.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# --- Événements de la salle (serveur → client) ------------------------------------------------


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
    # Le premier tour : le client relit la salle pour son item
    round_number: int
    round_count: int
    # Fin du timer du tour, si la salle en a un
    ends_at: datetime | None


class GameStartedEvent(BaseModel):
    """Le room admin a lancé une partie : le premier item est montré à tous."""

    type: Literal["game.started"] = "game.started"
    room_version: int
    data: GameStartedData


class RoomSettingsUpdatedData(BaseModel):
    pass


class RoomSettingsUpdatedEvent(BaseModel):
    """Le room admin a changé les réglages : le client relit la salle."""

    type: Literal["room.settings_updated"] = "room.settings_updated"
    room_version: int
    data: RoomSettingsUpdatedData = Field(default_factory=RoomSettingsUpdatedData)


# Union discriminée sur type : les événements qui changent la salle (et sa version)
RoomEvent = Annotated[
    ParticipantJoinedEvent
    | ParticipantPresenceEvent
    | ParticipantRemovedEvent
    | RoomSettingsUpdatedEvent
    | GameStartedEvent,
    Field(discriminator="type"),
]


# --- Messages techniques du canal ---------------------------------------------------------------


class PingMessage(BaseModel):
    """Battement de cœur du serveur : le client répond pong."""

    type: Literal["ping"] = "ping"


class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"


class AuthMessage(BaseModel):
    """Premier message du client : l'access token d'un compte, ou None pour un invité (reconnu par
    son cookie). Le token ne passe jamais dans l'URL."""

    type: Literal["auth"] = "auth"
    access_token: str | None = None


# Ce que le serveur envoie, et ce que le client peut envoyer
RoomServerMessage = Annotated[
    ParticipantJoinedEvent
    | ParticipantPresenceEvent
    | ParticipantRemovedEvent
    | RoomSettingsUpdatedEvent
    | GameStartedEvent
    | PingMessage,
    Field(discriminator="type"),
]
RoomClientMessage = Annotated[AuthMessage | PongMessage, Field(discriminator="type")]
