"""Réponses de l'API pour les salles, construites pour le lecteur qui les demande : un compte ou
un invité, room admin ou non (docs/technical/rooms.md)."""

import uuid

from app.api.presenters.images import optional_image_url
from app.models.enums import GameStatus, PlacementPhase
from app.models.game import Game
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.schemas.rooms import (
    CurrentGameResponse,
    CurrentItemResponse,
    GameTierResponse,
    GuestRoomResponse,
    OwnPlacementResponse,
    ParticipantResponse,
    RoomBanResponse,
    RoomResponse,
    RoomSettingsResponse,
    RoomTemplateResponse,
)
from app.services.image_storage import ImageStorage
from app.services.rooms import GuestSeat, RoomService


def room_response(
    room: Room, seat: Participant, service: RoomService, storage: ImageStorage
) -> RoomResponse:
    """La salle vue par le lecteur qui a cette place : compte ou invité (jamais room admin)."""
    participants: list[ParticipantResponse] = []
    for participant in service.seated_participants(room):
        participant_response: ParticipantResponse = ParticipantResponse(
            id=participant.id,
            display_name=participant.display_name,
            is_admin=participant.user_id == room.admin_id,
            is_guest=participant.is_guest,
            connected=participant.connected,
            is_you=participant.id == seat.id,
        )
        participants.append(participant_response)
    # None une fois le template purgé
    template: RoomTemplateResponse | None = (
        RoomTemplateResponse.model_validate(room.template) if room.template is not None else None
    )
    settings: RoomSettingsResponse = RoomSettingsResponse.model_validate(room)
    link: str = service.link(room)
    is_admin: bool = seat.user_id == room.admin_id
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
        game=current_game_response(room.current_game, seat, storage),
    )


def current_game_response(
    game: Game | None, seat: Participant, storage: ImageStorage
) -> CurrentGameResponse | None:
    """La partie en cours vue par ce lecteur : son tour, son item, qui l'a placé, et les
    placements du lecteur seulement (plateau privé) : ceux du tour pendant les tours, les finaux
    pendant le cooldown, avec les items qui lui manquent."""
    if game is None:
        return None
    current_round: Round = game.current_round
    tiers: list[GameTierResponse] = [
        GameTierResponse(id=tier.id, name=tier.name, color=tier.color)
        for tier in game.snapshot.tiers
    ]
    round_placements: list[Placement] = [
        placement
        for placement in game.placements
        if placement.phase == PlacementPhase.ROUND and not placement.is_absent
    ]
    # Partie en cours : ses placements appartiennent encore aux places (participant_id)
    placed_participant_ids: list[uuid.UUID] = [
        placement.participant_id
        for placement in round_placements
        if placement.snapshot_tile_id == current_round.snapshot_tile_id
        and placement.participant_id is not None
    ]
    # Le room admin qui ne joue pas n'a ni plateau ni item manqué (US-3.5)
    seat_places: bool = game.admin_plays or seat.user_id != seat.room.admin_id
    # Le plateau du lecteur pour la phase en cours, sans ses votes absents
    board_phase: PlacementPhase = (
        PlacementPhase.FINAL if game.status == GameStatus.COOLDOWN else PlacementPhase.ROUND
    )
    board: list[Placement] = [
        placement
        for placement in game.placements
        if placement.participant_id == seat.id
        and placement.phase == board_phase
        and not placement.is_absent
    ]
    # Rang de chaque tier, de haut en bas : trie les placements du lecteur tier par tier
    tier_ranks: dict[uuid.UUID, int] = {tier.id: tier.position for tier in game.snapshot.tiers}
    own_placements: list[OwnPlacementResponse] = []
    for placement in board:
        # Sans vote absent dans board : le tier et la position sont connus
        if placement.snapshot_tier_id is None or placement.position is None:
            continue
        own_placement: OwnPlacementResponse = OwnPlacementResponse(
            item=_item_response(placement.tile, storage),
            tier_id=placement.snapshot_tier_id,
            position=placement.position,
        )
        own_placements.append(own_placement)
    own_placements.sort(key=lambda own: (tier_ranks[own.tier_id], own.position))
    # Pendant le cooldown, chaque item de la partie sans placement final reste à placer (US-4.6)
    missed_items: list[CurrentItemResponse] = []
    if game.status == GameStatus.COOLDOWN and seat_places:
        placed_tile_ids: set[uuid.UUID] = {placement.snapshot_tile_id for placement in board}
        missed_items = [
            _item_response(game_round.tile, storage)
            for game_round in game.rounds
            if game_round.snapshot_tile_id not in placed_tile_ids
        ]
    return CurrentGameResponse(
        status=game.status,
        round_number=current_round.number,
        round_count=len(game.rounds),
        current_item=_item_response(current_round.tile, storage),
        ends_at=current_round.ends_at,
        tiers=tiers,
        placed_participant_ids=placed_participant_ids,
        own_placements=own_placements,
        cooldown_ends_at=game.cooldown_ends_at,
        missed_items=missed_items,
    )


def _item_response(tile: SnapshotTile, storage: ImageStorage) -> CurrentItemResponse:
    """Un item de la partie : une tuile de la version figée, son texte et son image."""
    return CurrentItemResponse(
        id=tile.id, text=tile.text, image_url=optional_image_url(storage, tile.image)
    )


def guest_room_response(
    seat: GuestSeat, service: RoomService, storage: ImageStorage
) -> GuestRoomResponse:
    room: RoomResponse = room_response(seat.room, seat.participant, service, storage)
    return GuestRoomResponse(
        **room.model_dump(),
        guest_link=service.guest_link(seat),
        guest_link_expires_at=seat.expires_at,
    )
