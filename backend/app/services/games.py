"""Règles métier des parties : démarrage et placements (docs/technical/games.md).

Le service possède la frontière de transaction : le démarrage fige le template, crée la partie et
ses tours et passe la salle en partie dans un seul commit ; un placement est enregistré sous le
verrou de la salle. Les événements sont publiés aux sockets de la salle après le commit.
L'enchaînement des tours et le cooldown viennent avec #93 et #96.
"""

import logging
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.exceptions.games import (
    GameInProgressError,
    ItemNotCurrentError,
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
from app.schemas.room_events import (
    GameStartedData,
    GameStartedEvent,
    ParticipantPlacedData,
    ParticipantPlacedEvent,
)
from app.services.room_channel import RoomEventPublisher
from app.services.rooms import RoomService, RoomViewer
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


def shuffle_items(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
    """Ordre aléatoire des items (réglage « aléatoire ») ; remplacé dans les tests."""
    shuffled: list[SnapshotTile] = list(tiles)
    random.SystemRandom().shuffle(shuffled)
    return shuffled


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
    ) -> None:
        # rooms et templates partagent cette session : tout tient dans la même transaction
        self._session = session
        self._publisher = publisher
        self._rooms = rooms
        self._templates = templates

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
        if room.auto_advance == AutoAdvance.TIMER:
            # Enregistrée seulement : la fin du tour à l'échéance vient avec #93
            first_round.ends_at = now + timedelta(seconds=room.timer_seconds)
        game: Game = Game(
            room_id=room.id,
            snapshot=snapshot,
            item_order=room.item_order,
            admin_plays=room.admin_plays,
            current_round_number=first_round.number,
            started_at=now,
            rounds=rounds,
        )
        self._session.add(game)
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
        """Place l'item en cours dans un tier, à une position (US-3.3) ; le replacer pendant le
        même tour remplace le placement. Renvoie la place du lecteur (sa salle : seat.room).
        Seul le premier placement du tour est diffusé, sans tier ni position (plateau privé)."""
        seat: Participant = self._rooms.seat_of(viewer, code, for_update=True)
        room: Room = seat.room
        game: Game | None = room.current_game
        if game is None or game.status != GameStatus.IN_ROUND:
            raise RoundNotInProgressError
        if seat not in self.placing_participants(room):
            raise NotAPlacingParticipantError
        current_round: Round = game.current_round
        # Un item passé ne bouge pas avant le cooldown, un item futur n'est pas encore montré
        if tile_id != current_round.snapshot_tile_id:
            raise ItemNotCurrentError
        if not any(tier.id == tier_id for tier in game.snapshot.tiers):
            raise TierNotFoundError

        # Le plateau du lecteur pour cette phase : ses placements de tour dans cette partie
        board: list[Placement] = [
            placement
            for placement in game.placements
            if placement.participant_id == seat.id and placement.phase == PlacementPhase.ROUND
        ]
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
        if first_placement:
            room.version += 1
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
                    room_version=room.version,
                    data=ParticipantPlacedData(
                        participant_id=seat.id, round_number=current_round.number
                    ),
                ),
            )
        return seat
