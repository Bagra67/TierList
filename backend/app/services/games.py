"""Règles métier des parties : démarrage (docs/technical/games.md).

Le service possède la frontière de transaction : le démarrage fige le template, crée la partie et
ses tours et passe la salle en partie dans un seul commit, puis publie l'événement aux sockets de
la salle. Les placements, l'enchaînement des tours et le cooldown viennent avec #92, #93 et #96.
"""

import logging
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions.games import GameInProgressError, NoPlacingParticipantError
from app.exceptions.rooms import RoomAdminRequiredError
from app.exceptions.templates import TemplateNotFoundError
from app.models.game import Game
from app.models.participant import Participant
from app.models.room import AutoAdvance, ItemOrder, Room, RoomStatus
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.schemas.room_events import GameStartedData, GameStartedEvent
from app.services.room_channel import RoomEventPublisher
from app.services.rooms import RoomService
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


def shuffle_items(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
    """Ordre aléatoire des items (réglage « aléatoire ») ; remplacé dans les tests."""
    shuffled: list[SnapshotTile] = list(tiles)
    random.SystemRandom().shuffle(shuffled)
    return shuffled


class GameService:
    def __init__(self, session: Session, settings: Settings, publisher: RoomEventPublisher) -> None:
        self._session = session
        self._settings = settings
        self._publisher = publisher
        self._rooms = RoomService(session, settings, publisher)

    def start(self, user: User, code: str) -> Room:
        """Lance une partie (room admin seulement, US-3.1) : fige la version courante du template,
        fixe l'ordre des items, crée un tour par tuile et montre le premier item à tous."""
        room: Room = self._rooms.get_for_change(user, code)
        if room.admin_id != user.id:
            raise RoomAdminRequiredError
        if room.status == RoomStatus.PLAYING:
            raise GameInProgressError
        # Template purgé : aucune nouvelle partie ne peut démarrer dans la salle
        if room.template_id is None:
            raise TemplateNotFoundError
        if not self.placing_participants(room):
            raise NoPlacingParticipantError

        # Le template de la salle est celui de son room admin ; il reste verrouillé jusqu'au commit
        snapshot: TemplateSnapshot = TemplateService(self._session, self._settings).take_snapshot(
            user, room.template_id
        )
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
