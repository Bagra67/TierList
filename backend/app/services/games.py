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


def _freeze_players(game: Game) -> None:
    """Clôture (US-5.1) : un joueur figé par place qui a des placements dans la partie (joueurs et
    retardataires, jamais le room admin qui ne joue pas), avec son compte et son nom. Ses
    placements passent de la place au joueur : fermer la salle, retirer la place ou supprimer le
    compte ne touche plus la partie close."""
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
        self._schedule_first_round(game)
        return self._reloaded(room.id)

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
            return self._reloaded_seat(room.id, seat.id)
        current_round: Round = game.current_round
        # Le timer n'est peut-être pas encore passé (threadpool chargé, redémarrage) : la fin du
        # tour compte déjà, un placement en retard ne peut plus le terminer
        if current_round.ends_at is not None and datetime.now(UTC) >= current_round.ends_at:
            raise RoundNotInProgressError
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
        return self._reloaded_seat(room.id, seat.id)

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
        return self._reloaded(room.id)

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

    def set_presence(self, participant_id: uuid.UUID, connected: bool) -> None:
        """Présence d'une place (canal temps réel, US-3.4). Pendant une partie, un départ comme
        un retour peut terminer le tour : « tout le monde a placé » ne compte que les connectés,
        et n'avance jamais une salle vide, que le retour d'un joueur qui a placé débloque."""
        changed: Room | None = self._rooms.set_presence(participant_id, connected)
        if changed is not None and changed.status == RoomStatus.PLAYING:
            self.advance_if_everyone_placed(changed.id)

    def remove_participant(
        self, user: User, code: str, participant_id: uuid.UUID, ban: bool
    ) -> Room:
        """Retire une place (room admin seulement, US-2.11), même pendant une partie : le retiré
        n'est plus attendu, il était peut-être le dernier à placer l'item en cours."""
        room: Room = self._rooms.remove_participant(user, code, participant_id, ban)
        self.advance_if_everyone_placed(room.id)
        return self._reloaded(room.id)

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
        return self._reloaded(room.id)

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
        """La salle relue en une fois après un commit, qui l'a expirée : la réponse la
        rechargerait sinon objet par objet, une requête par tuile."""
        room: Room | None = room_repository.get_room_by_id(self._session, room_id)
        if room is None:
            raise RoomNotFoundError
        return room

    def _reloaded_seat(self, room_id: uuid.UUID, seat_id: uuid.UUID) -> Participant:
        """La place du lecteur, dans sa salle relue après un commit (_reloaded)."""
        room: Room = self._reloaded(room_id)
        seat: Participant | None = next(
            (participant for participant in room.participants if participant.id == seat_id), None
        )
        if seat is None:
            raise RoomNotFoundError
        return seat

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
            and placement.participant_id is not None
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
        """Termine le cooldown, sous le verrou de la salle, sans commit : les classements sont
        finaux et la partie close, ses joueurs figés (US-4.1, US-5.1). La salle redevient ouverte
        dans la même transaction : « une partie en cours » vit dans les deux tables
        (docs/technical/games.md)."""
        game.status = GameStatus.CLOSED
        game.closed_at = datetime.now(UTC)
        _freeze_players(game)
        room.status = RoomStatus.OPEN
        room.version += 1
        logger.info("Partie close : room_id=%s game_id=%s", room.id, game.id)
        return GameClosedEvent(room_version=room.version, data=GameClosedData(game_id=game.id))

    def _announce_round_end(
        self, room: Room, game: Game, round_end: RoundStartedEvent | CooldownStartedEvent
    ) -> None:
        """Après le commit : programme l'échéance qui suit, puis publie la fin du tour.
        L'échéance vient de l'événement, figé sous le verrou : relire la partie ici pourrait voir
        la transition suivante d'un autre thread."""
        if isinstance(round_end, CooldownStartedEvent):
            self._scheduler.schedule_cooldown_end(game.id, round_end.data.ends_at)
        elif round_end.data.ends_at is not None:
            self._scheduler.schedule(game.id, round_end.data.round_number, round_end.data.ends_at)
        self._publisher.publish(room.id, round_end)

    def _schedule_first_round(self, game: Game) -> None:
        """Après le démarrage : le timer du premier tour, si la salle en a un."""
        first_round: Round = game.current_round
        if first_round.ends_at is not None:
            self._scheduler.schedule(game.id, first_round.number, first_round.ends_at)
