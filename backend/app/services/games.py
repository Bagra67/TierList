"""Règles métier des parties : démarrage, placements, enchaînement des tours et cooldown final
(docs/technical/games.md).

Le service possède la frontière de transaction : le démarrage fige le template, crée la partie et
ses tours et passe la salle en partie dans un seul commit ; un placement, la fin d'un tour et la
fin du cooldown sont enregistrés sous le verrou de la salle. Les événements sont publiés aux
sockets de la salle après le commit, puis l'échéance suivante (tour ou cooldown) est programmée.
"""

import logging
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.exceptions.games import (
    CooldownNotInProgressError,
    GameInProgressError,
    ItemNotCurrentError,
    ItemNotInGameError,
    NoPlacingParticipantError,
    NotAPlacingParticipantError,
    RoundNotInProgressError,
)
from app.exceptions.templates import TemplateNotFoundError, TierNotFoundError
from app.models.enums import AutoAdvance, GameStatus, ItemOrder, PlacementPhase, RoomStatus
from app.models.game import Game
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
from app.services.room_channel import RoomEventPublisher
from app.services.rooms import RoomService, RoomViewer
from app.services.round_timers import RoundScheduler
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


def shuffle_items(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
    """Ordre aléatoire des items (réglage « aléatoire ») ; remplacé dans les tests."""
    shuffled: list[SnapshotTile] = list(tiles)
    random.SystemRandom().shuffle(shuffled)
    return shuffled


def _board(game: Game, seat: Participant, phase: PlacementPhase) -> list[Placement]:
    """Le plateau d'une place pour une phase : ses placements de tour, ou ses placements finaux."""
    return [
        placement
        for placement in game.placements
        if placement.participant_id == seat.id and placement.phase == phase
    ]


def _start_final_boards(game: Game) -> None:
    """Début du cooldown : chaque placement de tour (sauf les votes absents) est copié en
    placement final, au même tier et à la même position. Un item que personne ne déplace garde
    donc un placement final égal à celui du tour (US-4.2) ; déplacer ne change que la copie."""
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


def _ensure_tier_in_game(game: Game, tier_id: uuid.UUID) -> None:
    if not any(tier.id == tier_id for tier in game.snapshot.tiers):
        raise TierNotFoundError


def _in_tier(board: list[Placement], tier_id: uuid.UUID, excluded: Placement) -> list[Placement]:
    """Placements du plateau dans ce tier, dans l'ordre de leurs positions, sans excluded."""
    in_tier: list[Placement] = [
        placement
        for placement in board
        if placement.snapshot_tier_id == tier_id and placement is not excluded
    ]
    return sorted(in_tier, key=lambda placement: placement.position or 0)


def _renumber(placements: list[Placement]) -> None:
    """Positions continues 0..n-1 dans l'ordre de la liste."""
    for position, placement in enumerate(placements):
        placement.position = position


def _place_in_tier(
    board: list[Placement], placement: Placement, tier_id: uuid.UUID, position: int
) -> None:
    """Met le placement à cette position du tier (au-delà de la fin, en dernier) et décale les
    suivants ; son ancien tier se referme. Les positions restent continues dans chaque tier, et
    l'ordre des autres items ne change pas (docs/technical/games.md)."""
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
        publisher: RoomEventPublisher,
        rooms: RoomService,
        templates: TemplateService,
        scheduler: RoundScheduler,
    ) -> None:
        # rooms et templates partagent cette session : tout tient dans la même transaction
        self._session = session
        self._publisher = publisher
        self._rooms = rooms
        self._templates = templates
        self._scheduler = scheduler

    def start(self, user: User, code: str) -> Room:
        """Lance une partie (room admin seulement, US-3.1) : fige la version courante du template,
        fixe l'ordre des items, crée un tour par tuile et montre le premier item à tous."""
        room: Room = self._rooms.get_for_admin_change(user, code)
        if room.status == RoomStatus.PLAYING:
            raise GameInProgressError
        # Template purgé : aucune nouvelle partie ne peut démarrer dans la salle
        if room.template_id is None:
            raise TemplateNotFoundError
        if not self.placing_participants(room):
            raise NoPlacingParticipantError

        # Le template de la salle est celui de son room admin ; il reste verrouillé jusqu'au commit
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
        self._schedule_current_round(game)
        return room

    def placing_participants(self, room: Room) -> list[Participant]:
        """Participants qui placent les items : tous, sauf le room admin quand il ne joue pas
        (US-3.5) ; il garde alors seulement les commandes."""
        return [
            participant
            for participant in self._rooms.seated_participants(room)
            if room.admin_plays or participant.user_id != room.admin_id
        ]

    def place(
        self, viewer: RoomViewer, code: str, tile_id: uuid.UUID, tier_id: uuid.UUID, position: int
    ) -> Participant:
        """Place une tuile dans un tier, à une position. Pendant un tour (US-3.3) : l'item en
        cours seulement ; le replacer pendant le même tour remplace le placement. Pendant le
        cooldown final (US-4.1, US-4.6) : n'importe quel item de la partie, en placement final.
        Renvoie la place du lecteur (sa salle : seat.room). Seul le premier placement d'un tour
        est diffusé, sans tier ni position (plateau privé)."""
        seat: Participant = self._rooms.seat_of(viewer, code, for_update=True)
        room: Room = seat.room
        game: Game | None = room.current_game
        if game is None:
            raise RoundNotInProgressError
        if seat not in self.placing_participants(room):
            raise NotAPlacingParticipantError
        if game.status == GameStatus.COOLDOWN:
            self._place_final(seat, game, tile_id, tier_id, position)
            return seat
        current_round: Round = game.current_round
        # Un item passé ne bouge pas avant le cooldown, un item futur n'est pas encore montré
        if tile_id != current_round.snapshot_tile_id:
            raise ItemNotCurrentError
        _ensure_tier_in_game(game, tier_id)

        # Le plateau du lecteur pour cette phase : ses placements de tour dans cette partie
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
        # Un déplacement ne change rien pour les autres : ni version, ni événement
        placed_version: int = room.version
        round_end: RoundStartedEvent | CooldownStartedEvent | None = None
        if first_placement:
            room.version += 1
            placed_version = room.version
            # Le dernier participant connecté attendu vient de placer : le tour se termine
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
            self._announce_round_end(room, game, round_end)
        return seat

    def next_round(self, user: User, code: str) -> Room:
        """Termine le tour en cours (room admin seulement, US-3.4), quel que soit le réglage
        automatique et même si des participants n'ont pas placé l'item."""
        room: Room = self._rooms.get_for_admin_change(user, code)
        game: Game | None = room.current_game
        if game is None or game.status != GameStatus.IN_ROUND:
            raise RoundNotInProgressError
        round_end: RoundStartedEvent | CooldownStartedEvent = self._end_round(room, game)
        self._session.commit()
        self._announce_round_end(room, game, round_end)
        return room

    def end_round_on_timer(self, game_id: uuid.UUID, round_number: int) -> None:
        """Termine le tour à la fin de son timer. Sans effet si ce tour n'est plus en cours : le
        « suivant » ou « tout le monde a placé » l'a terminé avant (transition idempotente)."""
        room: Room | None = self._locked_room_of_game(game_id)
        game: Game | None = room.current_game if room is not None else None
        if (
            room is None
            or game is None
            or game.id != game_id
            or game.status != GameStatus.IN_ROUND
            or game.current_round_number != round_number
        ):
            # Le commit libère seulement le verrou
            self._session.commit()
            return
        round_end: RoundStartedEvent | CooldownStartedEvent = self._end_round(room, game)
        self._session.commit()
        self._announce_round_end(room, game, round_end)

    def advance_if_everyone_placed(self, room_id: uuid.UUID) -> None:
        """Termine le tour si tous les participants connectés qui placent ont placé l'item :
        après une déconnexion ou un retrait, qui retirent quelqu'un de l'attente."""
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
        self._announce_round_end(room, game, round_end)

    def end_cooldown(self, user: User, code: str) -> Room:
        """Termine le cooldown final avant son timer (room admin seulement, US-4.1) : la partie
        est close."""
        room: Room = self._rooms.get_for_admin_change(user, code)
        game: Game | None = room.current_game
        if game is None or game.status != GameStatus.COOLDOWN:
            raise CooldownNotInProgressError
        closed: GameClosedEvent = self._close_game(room, game)
        self._session.commit()
        self._publisher.publish(room.id, closed)
        return room

    def end_cooldown_on_timer(self, game_id: uuid.UUID) -> None:
        """Termine le cooldown à la fin de son timer. Sans effet s'il n'est plus en cours : le
        room admin l'a terminé avant (transition idempotente)."""
        room: Room | None = self._locked_room_of_game(game_id)
        game: Game | None = room.current_game if room is not None else None
        if room is None or game is None or game.id != game_id or game.status != GameStatus.COOLDOWN:
            # Le commit libère seulement le verrou
            self._session.commit()
            return
        closed: GameClosedEvent = self._close_game(room, game)
        self._session.commit()
        self._publisher.publish(room.id, closed)

    def pending_round_deadlines(self) -> list[tuple[uuid.UUID, int, datetime]]:
        """Échéances des tours en cours, à reprogrammer au démarrage du processus."""
        return game_repository.list_pending_round_deadlines(self._session)

    def pending_cooldown_ends(self) -> list[tuple[uuid.UUID, datetime]]:
        """Fins des cooldowns en cours, à reprogrammer au démarrage du processus."""
        return game_repository.list_pending_cooldown_ends(self._session)

    def _place_final(
        self, seat: Participant, game: Game, tile_id: uuid.UUID, tier_id: uuid.UUID, position: int
    ) -> None:
        """Pendant le cooldown : déplace un item du plateau final, ou y place un item manqué
        (vote absent, arrivée en retard), qui garde son vote absent de tour (US-4.6). Le plateau
        est privé : ni version, ni événement."""
        # Le timer n'est peut-être pas encore passé : la fin du cooldown compte déjà
        if game.cooldown_ends_at is not None and datetime.now(UTC) >= game.cooldown_ends_at:
            raise RoundNotInProgressError
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

    def _locked_room_of_game(self, game_id: uuid.UUID) -> Room | None:
        """La salle de la partie, verrouillée ; None si elle a été supprimée."""
        room_id: uuid.UUID | None = game_repository.get_room_id_of_game(self._session, game_id)
        if room_id is None:
            return None
        return room_repository.get_room_by_id(self._session, room_id, for_update=True)

    @staticmethod
    def _round_ends_at(room: Room, now: datetime) -> datetime | None:
        """Fin du timer d'un tour qui commence, si la salle passe à l'item suivant au timer."""
        if room.auto_advance != AutoAdvance.TIMER:
            return None
        return now + timedelta(seconds=room.timer_seconds)

    def _everyone_placed(self, room: Room, game: Game) -> bool:
        """Réglage « tout le monde a placé » : chaque participant connecté qui place a placé
        l'item en cours. Il en faut au moins un : personne de connecté (redémarrage du serveur,
        coupure générale) ne termine pas le tour."""
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
        }
        return all(participant.id in placed_ids for participant in connected)

    def _end_round(self, room: Room, game: Game) -> RoundStartedEvent | CooldownStartedEvent:
        """Termine le tour en cours, sous le verrou de la salle, sans commit : vote absent pour
        chaque participant qui place sans placement pour l'item (US-4.3), puis tour suivant, ou
        cooldown final après le dernier tour. Renvoie l'événement à publier après le commit."""
        now: datetime = datetime.now(UTC)
        ending: Round = game.current_round
        ending.ended_at = now
        placed_ids: set[uuid.UUID] = {
            placement.participant_id
            for placement in game.placements
            if placement.phase == PlacementPhase.ROUND
            and placement.snapshot_tile_id == ending.snapshot_tile_id
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
        """Termine le cooldown, sous le verrou de la salle, sans commit : les classements sont
        finaux et la partie close (US-4.1). La salle redevient ouverte dans la même transaction :
        « une partie en cours » vit dans les deux tables (docs/technical/games.md)."""
        game.status = GameStatus.CLOSED
        game.closed_at = datetime.now(UTC)
        room.status = RoomStatus.OPEN
        room.version += 1
        logger.info("Partie close : room_id=%s game_id=%s", room.id, game.id)
        return GameClosedEvent(room_version=room.version, data=GameClosedData(game_id=game.id))

    def _announce_round_end(
        self, room: Room, game: Game, round_end: RoundStartedEvent | CooldownStartedEvent
    ) -> None:
        """Après le commit : publie la fin du tour et programme l'échéance qui suit."""
        self._publisher.publish(room.id, round_end)
        self._schedule_current_round(game)

    def _schedule_current_round(self, game: Game) -> None:
        """Programme l'échéance de la phase en cours : le timer du tour, ou la fin du cooldown."""
        if game.status == GameStatus.COOLDOWN and game.cooldown_ends_at is not None:
            self._scheduler.schedule_cooldown_end(game.id, game.cooldown_ends_at)
            return
        if game.status != GameStatus.IN_ROUND:
            return
        current_round: Round = game.current_round
        if current_round.ends_at is not None:
            self._scheduler.schedule(game.id, current_round.number, current_round.ends_at)
