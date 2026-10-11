import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.constants.rooms import (
    COOLDOWN_SECONDS_MAX,
    COOLDOWN_SECONDS_MIN,
    TIMER_SECONDS_MAX,
    TIMER_SECONDS_MIN,
)
from app.models.room import AutoAdvance, ItemOrder, RoomStatus


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
    display_name: str
    is_admin: bool


class RoomResponse(BaseModel):
    code: str
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
