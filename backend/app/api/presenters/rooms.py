"""Réponses de l'API pour les salles, construites pour le lecteur qui les demande : un compte ou
un invité, room admin ou non (docs/technical/rooms.md)."""

from app.api.presenters.images import optional_image_url
from app.models.game import Game
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.user import User
from app.schemas.rooms import (
    CurrentGameResponse,
    CurrentItemResponse,
    GuestRoomResponse,
    ParticipantResponse,
    RoomBanResponse,
    RoomResponse,
    RoomSettingsResponse,
    RoomTemplateResponse,
)
from app.services.image_storage import ImageStorage
from app.services.rooms import GuestSeat, RoomService


def room_response(
    room: Room, user: User | None, service: RoomService, storage: ImageStorage
) -> RoomResponse:
    """La salle vue par ce lecteur : user est None pour un invité (jamais room admin)."""
    participants: list[ParticipantResponse] = []
    for participant in service.seated_participants(room):
        participant_response: ParticipantResponse = ParticipantResponse(
            id=participant.id,
            display_name=participant.display_name,
            is_admin=participant.user_id == room.admin_id,
            is_guest=participant.is_guest,
            connected=participant.connected,
        )
        participants.append(participant_response)
    # None une fois le template purgé
    template: RoomTemplateResponse | None = (
        RoomTemplateResponse.model_validate(room.template) if room.template is not None else None
    )
    settings: RoomSettingsResponse = RoomSettingsResponse.model_validate(room)
    link: str = service.link(room)
    is_admin: bool = user is not None and room.admin_id == user.id
    # Les bannissements ne regardent que le room admin
    bans: list[RoomBanResponse] = []
    if is_admin:
        for room_ban in room.bans:
            ban_response: RoomBanResponse = RoomBanResponse(
                id=room_ban.id, display_name=room_ban.display_name, is_guest=room_ban.is_guest
            )
            bans.append(ban_response)
    return RoomResponse(
        code=room.code,
        version=room.version,
        link=link,
        status=room.status,
        template=template,
        settings=settings,
        participants=participants,
        is_admin=is_admin,
        bans=bans,
        game=current_game_response(room.current_game, storage),
    )


def current_game_response(game: Game | None, storage: ImageStorage) -> CurrentGameResponse | None:
    """La partie en cours vue par tous : son tour et son item, jamais les placements."""
    if game is None:
        return None
    current_round: Round = game.current_round
    tile: SnapshotTile = current_round.tile
    current_item: CurrentItemResponse = CurrentItemResponse(
        id=tile.id, text=tile.text, image_url=optional_image_url(storage, tile.image)
    )
    return CurrentGameResponse(
        round_number=current_round.number,
        round_count=len(game.rounds),
        current_item=current_item,
        ends_at=current_round.ends_at,
    )


def guest_room_response(
    seat: GuestSeat, service: RoomService, storage: ImageStorage
) -> GuestRoomResponse:
    room: RoomResponse = room_response(seat.room, None, service, storage)
    return GuestRoomResponse(
        **room.model_dump(),
        guest_link=service.guest_link(seat),
        guest_link_expires_at=seat.expires_at,
    )
