import logging
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import generate_public_results_token
from app.exceptions.games import (
    CooldownNotInProgressError,
    CooldownOverError,
    GameInProgressError,
    ItemNotCurrentError,
    ItemNotInGameError,
    NoPlacingParticipantError,
    NotAPlacingParticipantError,
    RoundNotInProgressError,
)
from app.exceptions.rooms import RoomNotFoundError
from app.exceptions.templates import TemplateNotFoundError, TierNotFoundError
from app.models.enums import AutoAdvance, GameStatus, ItemOrder, PlacementPhase, RoomStatus
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.repositories import games as game_repository
from app.repositories import rooms as room_repository
from app.schemas.room_events import (
    CooldownStartedData,
    CooldownStartedEvent,
    GameClosedData,
    GameClosedEvent,
    GameStartedData,
    GameStartedEvent,
    ParticipantPlacedData,
    ParticipantPlacedEvent,
    RoundStartedData,
    RoundStartedEvent,
)
from app.services.room_channel import PostCommitRoomPublisher
from app.services.rooms import RoomService, RoomViewer
from app.services.round_timers import RoundScheduler
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


def shuffle_items(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
    shuffled: list[SnapshotTile] = list(tiles)
    random.SystemRandom().shuffle(shuffled)
    return shuffled


def _board(game: Game, seat: Participant, phase: PlacementPhase) -> list[Placement]:
    return [
        placement
        for placement in game.placements
        if placement.participant_id == seat.id and placement.phase == phase
    ]


def _start_final_boards(game: Game) -> None:
    round_placements: list[Placement] = [
        placement
        for placement in game.placements
        if placement.phase == PlacementPhase.ROUND and not placement.is_absent
    ]
    for round_placement in round_placements:
        final: Placement = Placement(
            participant_id=round_placement.participant_id,
            snapshot_tile_id=round_placement.snapshot_tile_id,
            phase=PlacementPhase.FINAL,
            snapshot_tier_id=round_placement.snapshot_tier_id,
            position=round_placement.position,
        )
        game.placements.append(final)


def _freeze_players(game: Game) -> None:
    players: dict[uuid.UUID, GamePlayer] = {}
    for placement in game.placements:
        participant: Participant | None = placement.participant
        if participant is None:
            continue
        player: GamePlayer | None = players.get(participant.id)
        if player is None:
            player = GamePlayer(user_id=participant.user_id, display_name=participant.display_name)
            game.players.append(player)
            players[participant.id] = player
        placement.player = player
        placement.participant = None


def _is_inactive(room: Room, cutoff: datetime) -> bool:
    return (
        room.status == RoomStatus.OPEN
        and room.updated_at < cutoff
        and not any(participant.connected for participant in room.participants)
    )


def _ensure_tier_in_game(game: Game, tier_id: uuid.UUID) -> None:
    if not any(tier.id == tier_id for tier in game.snapshot.tiers):
        raise TierNotFoundError


def _in_tier(board: list[Placement], tier_id: uuid.UUID, excluded: Placement) -> list[Placement]:
    in_tier: list[Placement] = [
        placement
        for placement in board
        if placement.snapshot_tier_id == tier_id and placement is not excluded
    ]
    return sorted(in_tier, key=lambda placement: placement.position or 0)


def _renumber(placements: list[Placement]) -> None:
    for position, placement in enumerate(placements):
        placement.position = position


def _place_in_tier(
    board: list[Placement], placement: Placement, tier_id: uuid.UUID, position: int
) -> None:
    old_tier_id: uuid.UUID | None = placement.snapshot_tier_id
    if old_tier_id is not None and old_tier_id != tier_id:
        _renumber(_in_tier(board, old_tier_id, excluded=placement))
    target: list[Placement] = _in_tier(board, tier_id, excluded=placement)
    target.insert(min(position, len(target)), placement)
    placement.snapshot_tier_id = tier_id
    _renumber(target)


class GameService:
    def __init__(
        self,
        session: Session,
        publisher: PostCommitRoomPublisher,
        rooms: RoomService,
        templates: TemplateService,
        scheduler: RoundScheduler,
    ) -> None:
        self._session = session
        self._publisher = publisher
        self._rooms = rooms
        self._templates = templates
        self._scheduler = scheduler

    def start(self, user: User, code: str) -> Room:
        room: Room = self._rooms.get_for_admin_change(user, code)
        if room.status == RoomStatus.PLAYING:
            raise GameInProgressError
        if room.template_id is None:
            raise TemplateNotFoundError
        if not self.placing_participants(room):
            raise NoPlacingParticipantError

        snapshot: TemplateSnapshot = self._templates.take_snapshot(user, room.template_id)
        tiles: list[SnapshotTile] = list(snapshot.tiles)
        if room.item_order == ItemOrder.RANDOM:
            tiles = shuffle_items(tiles)

        now: datetime = datetime.now(UTC)
        rounds: list[Round] = [
            Round(number=number, tile=tile) for number, tile in enumerate(tiles, start=1)
        ]
        first_round: Round = rounds[0]
        first_round.started_at = now
        first_round.ends_at = self._round_ends_at(room, now)
        game: Game = Game(
            room_id=room.id,
            admin_id=room.admin_id,
            snapshot=snapshot,
            item_order=room.item_order,
            admin_plays=room.admin_plays,
            current_round_number=first_round.number,
            started_at=now,
            rounds=rounds,
        )
        game_repository.add_game(self._session, game)
        room.status = RoomStatus.PLAYING
        room.version += 1
        self._session.commit()
        logger.info(
            "Partie lancée : room_id=%s game_id=%s rounds=%d item_order=%s",
            room.id,
            game.id,
            len(rounds),
            room.item_order,
        )
        self._publisher.publish(
            room.id,
            GameStartedEvent(
                room_version=room.version,
                data=GameStartedData(
                    round_number=first_round.number,
                    round_count=len(rounds),
                    ends_at=first_round.ends_at,
                ),
            ),
        )
        self._schedule_first_round(game)
        return self._reloaded(room.id)

    def placing_participants(self, room: Room) -> list[Participant]:
        return [
            participant
            for participant in self._rooms.seated_participants(room)
            if room.admin_plays or participant.user_id != room.admin_id
        ]

    def place(
        self, viewer: RoomViewer, code: str, tile_id: uuid.UUID, tier_id: uuid.UUID, position: int
    ) -> Participant:
        seat: Participant = self._rooms.seat_of(viewer, code, for_update=True)
        room: Room = seat.room
        game: Game | None = room.current_game
        if game is None:
            raise RoundNotInProgressError
        if seat not in self.placing_participants(room):
            raise NotAPlacingParticipantError
        if game.status == GameStatus.COOLDOWN:
            self._place_final(seat, game, tile_id, tier_id, position)
            return self._reloaded_seat(room.id, seat.id)
        current_round: Round = game.current_round
        if current_round.ends_at is not None and datetime.now(UTC) >= current_round.ends_at:
            raise RoundNotInProgressError
        if tile_id != current_round.snapshot_tile_id:
            raise ItemNotCurrentError
        _ensure_tier_in_game(game, tier_id)

        board: list[Placement] = _board(game, seat, PlacementPhase.ROUND)
        placement: Placement | None = next(
            (placement for placement in board if placement.snapshot_tile_id == tile_id), None
        )
        first_placement: bool = placement is None
        if placement is None:
            placement = Placement(
                participant_id=seat.id, snapshot_tile_id=tile_id, phase=PlacementPhase.ROUND
            )
            game.placements.append(placement)
        _place_in_tier(board, placement, tier_id, position)
        placed_version: int = room.version
        round_end: RoundStartedEvent | CooldownStartedEvent | None = None
        if first_placement:
            room.version += 1
            placed_version = room.version
            if self._everyone_placed(room, game):
                round_end = self._end_round(room, game)
        self._session.commit()
        logger.info(
            "Item placé : room_id=%s round=%d participant_id=%s first=%s",
            room.id,
            current_round.number,
            seat.id,
            first_placement,
        )
        if first_placement:
            self._publisher.publish(
                room.id,
                ParticipantPlacedEvent(
                    room_version=placed_version,
                    data=ParticipantPlacedData(
                        participant_id=seat.id, round_number=current_round.number
                    ),
                ),
            )
        if round_end is not None:
            self._announce_round_end(room.id, game.id, round_end)
        return self._reloaded_seat(room.id, seat.id)

    def next_round(self, user: User, code: str) -> Room:
        room: Room = self._rooms.get_for_admin_change(user, code)
        game: Game | None = room.current_game
        if game is None or game.status != GameStatus.IN_ROUND:
            raise RoundNotInProgressError
        round_end: RoundStartedEvent | CooldownStartedEvent = self._end_round(room, game)
        self._session.commit()
        self._announce_round_end(room.id, game.id, round_end)
        return self._reloaded(room.id)

    def end_round_on_timer(self, game_id: uuid.UUID, round_number: int) -> None:
        room: Room | None = self._locked_room_of_game(game_id)
        game: Game | None = room.current_game if room is not None else None
        if (
            room is None
            or game is None
            or game.id != game_id
            or game.status != GameStatus.IN_ROUND
            or game.current_round_number != round_number
        ):
            self._release_room_lock()
            return
        round_end: RoundStartedEvent | CooldownStartedEvent = self._end_round(room, game)
        self._session.commit()
        self._announce_round_end(room.id, game.id, round_end)

    def set_presence(self, participant_id: uuid.UUID, connected: bool) -> None:
        changed: Room | None = self._rooms.set_presence(participant_id, connected)
        if changed is not None and changed.status == RoomStatus.PLAYING:
            self.advance_if_everyone_placed(changed.id)

    def remove_participant(
        self, user: User, code: str, participant_id: uuid.UUID, ban: bool
    ) -> Room:
        room: Room = self._rooms.remove_participant(user, code, participant_id, ban)
        self.advance_if_everyone_placed(room.id)
        return self._reloaded(room.id)

    def advance_if_everyone_placed(self, room_id: uuid.UUID) -> None:
        room: Room | None = room_repository.get_room_by_id(self._session, room_id, for_update=True)
        game: Game | None = room.current_game if room is not None else None
        if (
            room is None
            or game is None
            or game.status != GameStatus.IN_ROUND
            or not self._everyone_placed(room, game)
        ):
            self._session.commit()
            return
        round_end: RoundStartedEvent | CooldownStartedEvent = self._end_round(room, game)
        self._session.commit()
        self._announce_round_end(room.id, game.id, round_end)

    def end_cooldown(self, user: User, code: str) -> Room:
        room: Room = self._rooms.get_for_admin_change(user, code)
        game: Game | None = room.current_game
        if game is None or game.status != GameStatus.COOLDOWN:
            raise CooldownNotInProgressError
        closed: GameClosedEvent = self._close_game(room, game)
        self._session.commit()
        self._publisher.publish(room.id, closed)
        return self._reloaded(room.id)

    def end_cooldown_on_timer(self, game_id: uuid.UUID) -> None:
        room: Room | None = self._locked_room_of_game(game_id)
        game: Game | None = room.current_game if room is not None else None
        if room is None or game is None or game.id != game_id or game.status != GameStatus.COOLDOWN:
            self._release_room_lock()
            return
        closed: GameClosedEvent = self._close_game(room, game)
        self._session.commit()
        self._publisher.publish(room.id, closed)

    def close_room(self, user: User, code: str) -> None:
        room: Room = self._rooms.get_for_admin_change(user, code)
        room_id: uuid.UUID = room.id
        self._close_room_locked(room, reason="admin")
        self._session.commit()
        self._publisher.close_room(room_id)

    def close_rooms_of_admin(self, user: User) -> None:
        room_ids: list[uuid.UUID] = room_repository.list_room_ids_of_admin(self._session, user.id)
        for room_id in room_ids:
            room: Room | None = room_repository.get_room_by_id(
                self._session, room_id, for_update=True
            )
            if room is None:
                self._session.commit()
                continue
            self._close_room_locked(room, reason="account_deleted")
            self._session.commit()
            self._publisher.close_room(room_id)

    def close_inactive_rooms(self, inactive_for: timedelta) -> int:
        cutoff: datetime = datetime.now(UTC) - inactive_for
        room_ids: list[uuid.UUID] = room_repository.list_inactive_room_ids(self._session, cutoff)
        closed_count: int = 0
        for room_id in room_ids:
            room: Room | None = room_repository.get_room_by_id(
                self._session, room_id, for_update=True
            )
            if room is None or not _is_inactive(room, cutoff):
                self._release_room_lock()
                continue
            self._close_room_locked(room, reason="inactive")
            self._session.commit()
            self._publisher.close_room(room_id)
            closed_count += 1
        return closed_count

    def pending_round_deadlines(self) -> list[tuple[uuid.UUID, int, datetime]]:
        return game_repository.list_pending_round_deadlines(self._session)

    def pending_cooldown_ends(self) -> list[tuple[uuid.UUID, datetime]]:
        return game_repository.list_pending_cooldown_ends(self._session)

    def _place_final(
        self, seat: Participant, game: Game, tile_id: uuid.UUID, tier_id: uuid.UUID, position: int
    ) -> None:
        if game.cooldown_ends_at is not None and datetime.now(UTC) >= game.cooldown_ends_at:
            raise CooldownOverError
        if not any(game_round.snapshot_tile_id == tile_id for game_round in game.rounds):
            raise ItemNotInGameError
        _ensure_tier_in_game(game, tier_id)
        board: list[Placement] = _board(game, seat, PlacementPhase.FINAL)
        placement: Placement | None = next(
            (placement for placement in board if placement.snapshot_tile_id == tile_id), None
        )
        caught_up: bool = placement is None
        if placement is None:
            placement = Placement(
                participant_id=seat.id, snapshot_tile_id=tile_id, phase=PlacementPhase.FINAL
            )
            game.placements.append(placement)
        _place_in_tier(board, placement, tier_id, position)
        self._session.commit()
        logger.info(
            "Placement final : game_id=%s participant_id=%s caught_up=%s",
            game.id,
            seat.id,
            caught_up,
        )

    def _reloaded(self, room_id: uuid.UUID) -> Room:
        room: Room | None = room_repository.get_room_by_id(self._session, room_id)
        if room is None:
            raise RoomNotFoundError
        return room

    def _reloaded_seat(self, room_id: uuid.UUID, seat_id: uuid.UUID) -> Participant:
        room: Room = self._reloaded(room_id)
        seat: Participant | None = next(
            (participant for participant in room.participants if participant.id == seat_id), None
        )
        if seat is None:
            raise RoomNotFoundError
        return seat

    def _locked_room_of_game(self, game_id: uuid.UUID) -> Room | None:
        room_id: uuid.UUID | None = game_repository.get_room_id_of_game(self._session, game_id)
        if room_id is None:
            return None
        return room_repository.get_room_by_id(self._session, room_id, for_update=True)

    @staticmethod
    def _round_ends_at(room: Room, now: datetime) -> datetime | None:
        if room.auto_advance != AutoAdvance.TIMER:
            return None
        return now + timedelta(seconds=room.timer_seconds)

    def _everyone_placed(self, room: Room, game: Game) -> bool:
        if room.auto_advance != AutoAdvance.EVERYONE_PLACED:
            return False
        connected: list[Participant] = [
            participant for participant in self.placing_participants(room) if participant.connected
        ]
        if not connected:
            return False
        current_tile_id: uuid.UUID = game.current_round.snapshot_tile_id
        placed_ids: set[uuid.UUID] = {
            placement.participant_id
            for placement in game.placements
            if placement.phase == PlacementPhase.ROUND
            and placement.snapshot_tile_id == current_tile_id
            and not placement.is_absent
            and placement.participant_id is not None
        }
        return all(participant.id in placed_ids for participant in connected)

    def _end_round(self, room: Room, game: Game) -> RoundStartedEvent | CooldownStartedEvent:
        now: datetime = datetime.now(UTC)
        ending: Round = game.current_round
        ending.ended_at = now
        placed_ids: set[uuid.UUID] = {
            placement.participant_id
            for placement in game.placements
            if placement.phase == PlacementPhase.ROUND
            and placement.snapshot_tile_id == ending.snapshot_tile_id
            and placement.participant_id is not None
        }
        for participant in self.placing_participants(room):
            if participant.id not in placed_ids:
                absent: Placement = Placement(
                    participant_id=participant.id,
                    snapshot_tile_id=ending.snapshot_tile_id,
                    phase=PlacementPhase.ROUND,
                )
                game.placements.append(absent)
        room.version += 1
        logger.info(
            "Tour terminé : room_id=%s game_id=%s round=%d", room.id, game.id, ending.number
        )
        if ending.number < len(game.rounds):
            game.current_round_number = ending.number + 1
            next_round: Round = game.current_round
            next_round.started_at = now
            next_round.ends_at = self._round_ends_at(room, now)
            return RoundStartedEvent(
                room_version=room.version,
                data=RoundStartedData(
                    round_number=next_round.number,
                    round_count=len(game.rounds),
                    ends_at=next_round.ends_at,
                ),
            )
        cooldown_ends_at: datetime = now + timedelta(seconds=room.cooldown_seconds)
        game.status = GameStatus.COOLDOWN
        game.cooldown_ends_at = cooldown_ends_at
        _start_final_boards(game)
        return CooldownStartedEvent(
            room_version=room.version, data=CooldownStartedData(ends_at=cooldown_ends_at)
        )

    def _close_game(self, room: Room, game: Game) -> GameClosedEvent:
        game.status = GameStatus.CLOSED
        game.closed_at = datetime.now(UTC)
        game.public_token = generate_public_results_token()
        _freeze_players(game)
        room.status = RoomStatus.OPEN
        room.version += 1
        logger.info("Partie close : room_id=%s game_id=%s", room.id, game.id)
        return GameClosedEvent(room_version=room.version, data=GameClosedData(game_id=game.id))

    def _close_room_locked(self, room: Room, reason: str) -> None:
        game: Game | None = room.current_game
        if game is not None:
            if game.status == GameStatus.IN_ROUND:
                game.current_round.ended_at = datetime.now(UTC)
                _start_final_boards(game)
            self._close_game(room, game)
            self._session.flush()
        room_repository.delete_room(self._session, room)
        logger.info("Salle fermée : room_id=%s reason=%s", room.id, reason)

    def _announce_round_end(
        self,
        room_id: uuid.UUID,
        game_id: uuid.UUID,
        round_end: RoundStartedEvent | CooldownStartedEvent,
    ) -> None:
        if isinstance(round_end, CooldownStartedEvent):
            self._scheduler.schedule_cooldown_end(game_id, round_end.data.ends_at)
        elif round_end.data.ends_at is not None:
            self._scheduler.schedule(game_id, round_end.data.round_number, round_end.data.ends_at)
        self._publisher.publish(room_id, round_end)

    def _release_room_lock(self) -> None:
        self._session.commit()

    def _schedule_first_round(self, game: Game) -> None:
        first_round: Round = game.current_round
        if first_round.ends_at is not None:
            self._scheduler.schedule(game.id, first_round.number, first_round.ends_at)
