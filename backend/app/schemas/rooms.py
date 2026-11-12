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
    """Modèle de la nouvelle salle."""

    template_id: uuid.UUID


TimerSeconds = Annotated[int, Field(ge=TIMER_SECONDS_MIN, le=TIMER_SECONDS_MAX)]
CooldownSeconds = Annotated[int, Field(ge=COOLDOWN_SECONDS_MIN, le=COOLDOWN_SECONDS_MAX)]


class UpdateRoomSettingsRequest(BaseModel):
    """Changements des réglages de la salle : seuls les champs envoyés changent ; une requête sans
    champ ne change rien."""

    item_order: ItemOrder | None = None
    auto_advance: AutoAdvance | None = None
    timer_seconds: TimerSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    admin_plays: bool | None = None
    late_arrivals_allowed: bool | None = None


class RoomSettingsResponse(BaseModel):
    """Réglages appliqués à la prochaine partie. `timer_seconds` est gardé même quand `auto_advance`
    n'est pas `timer`."""

    model_config = ConfigDict(from_attributes=True)

    item_order: ItemOrder
    auto_advance: AutoAdvance
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


class RoomTemplateResponse(BaseModel):
    """Modèle de la salle ; `hidden` est vrai quand la modération l'a masqué : aucune nouvelle
    partie ne peut alors commencer."""

    id: uuid.UUID
    name: str
    hidden: bool


class ParticipantResponse(BaseModel):
    """Une place dans la salle : un compte avec son nom affiché, ou un invité avec son pseudo.
    `is_you` désigne la place du lecteur."""

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
    """La partie en cours, vue par le lecteur : seuls ses propres placements sont envoyés, avec la
    liste de ceux qui ont placé l'item du tour. `ends_at` est la fin du tour quand il a un minuteur
    ; `cooldown_ends_at` et `missed_items` servent pendant le cooldown final."""

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
    """Tier choisi pour l'item, et position dans ce tier (0 = premier) ; une position au-delà de la
    fin met l'item en dernier."""

    tier_id: uuid.UUID
    position: Annotated[int, Field(ge=0)]


class RoomBanResponse(BaseModel):
    """Un bannissement de la salle, visible de l'admin seulement."""

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
    """Une salle vue par un participant. `version` augmente à chaque changement de la salle ; `bans`
    n'est rempli que pour l'admin ; `template` est null quand le modèle a été purgé ; `game` est
    null hors partie."""

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
    """Pseudo de l'invité dans la salle."""

    nickname: DisplayName


class RestoreGuestRequest(BaseModel):
    """Token du lien perso de l'invité."""

    token: str


class GuestRoomResponse(RoomResponse):
    """Salle rejointe en invité, avec le lien perso : donné une seule fois, la base n'en gardant
    que l'empreinte."""

    guest_link: str
    guest_link_expires_at: datetime
