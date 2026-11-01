"""Parties terminées du jeu de données, écrites directement dans l'état que laisse la clôture d'une
partie (GameService._close_game) : instantané du modèle, tours, joueurs figés, placements de tour
et finaux, lien des résultats.

Jouer chaque partie par le service (un placement à la fois) recharge la salle à chaque appel :
des centaines de milliers de requêtes, trop lent sur staging, à travers Internet. Les règles de la
clôture sont donc reprises ici : un joueur figé par personne qui place ; un vote absent est un
placement de tour sans tier ; seuls les items placés ont un placement final ; les positions
restent continues dans chaque tier."""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import generate_public_results_token
from app.models.enums import GameStatus, ItemOrder, PlacementPhase
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.placement import Placement
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tier import SnapshotTier
from app.models.snapshot_tile import SnapshotTile
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.seed.sizes import SeedSize
from app.services.rooms import RoomService
from app.services.templates import TemplateService

GUEST_NICKNAMES: tuple[str, ...] = (
    "Lou", "Max", "Tom", "Eva", "Noé", "Mia", "Léo", "Jade", "Ana", "Kim", "Ugo", "Liv",
)  # fmt: skip
# Part des placements manqués (votes absents), et part des items que personne ne place
ABSENT_RATE = 0.12
NOBODY_PLACES_RATE = 0.04
# Les parties sont étalées sur cette durée, de la plus ancienne à aujourd'hui
HISTORY_SPAN_DAYS = 90
# Durée d'un tour et du cooldown final, pour dater les tours
ROUND_SECONDS = 30
COOLDOWN_SECONDS = 60
# Parties terminées de chaque salle qui reste ouverte : son lobby montre leurs résultats
GAMES_PER_LOBBY_ROOM = 2


@dataclass(frozen=True)
class SeedGames:
    closed: list[Game]
    # Salles qui restent ouvertes, avec leurs parties terminées
    lobby_rooms: list[Room]


@dataclass(frozen=True)
class _Player:
    # None pour un invité
    user: User | None
    name: str


def create_closed_games(
    session: Session,
    rooms: RoomService,
    templates: TemplateService,
    size: SeedSize,
    players: list[User],
    playable: list[Template],
    rng: random.Random,
) -> SeedGames:
    """Crée size.closed_games parties terminées, dont size.history_games avec le premier joueur
    (le long historique). Les premières appartiennent par deux à size.lobby_rooms salles qui
    restent ouvertes, avec leurs joueurs assis ; les autres n'ont plus de salle, comme une
    partie dont la salle a été fermée."""
    closed: list[Game] = []
    lobby_rooms: list[Room] = []
    lobby_games: int = size.lobby_rooms * GAMES_PER_LOBBY_ROOM
    room: Room | None = None
    admin: User = players[0]
    template: Template = playable[0]
    game_players: list[_Player] = []
    for index in range(size.closed_games):
        in_lobby_room: bool = index < lobby_games
        # La seconde partie d'une salle ouverte reprend sa salle, son room admin et ses joueurs
        if not in_lobby_room or index % GAMES_PER_LOBBY_ROOM == 0:
            template = playable[index % len(playable)]
            admin = next(player for player in players if player.id == template.owner_id)
            game_players = _pick_players(
                admin, players, with_history_player=index < size.history_games, rng=rng
            )
            room = None
            if in_lobby_room:
                room = _seat_in_new_room(rooms, admin, template, game_players)
                lobby_rooms.append(room)
        # Les plus anciennes d'abord : la dernière partie est d'aujourd'hui
        days_ago: float = HISTORY_SPAN_DAYS * (size.closed_games - 1 - index) / size.closed_games
        closed_at: datetime = datetime.now(UTC) - timedelta(
            days=days_ago, minutes=rng.randint(0, 600)
        )
        snapshot: TemplateSnapshot = templates.take_snapshot(admin, template.id)
        closed.append(_closed_game(session, room, admin, snapshot, game_players, closed_at, rng))
        session.commit()
    return SeedGames(closed=closed, lobby_rooms=lobby_rooms)


def _pick_players(
    admin: User, players: list[User], with_history_player: bool, rng: random.Random
) -> list[_Player]:
    """Le room admin (s'il joue), 1 à 5 autres comptes, le premier joueur s'il le faut, et 0 à 2
    invités : de 2 à 8 joueurs, assez pour une salle de 10 places."""
    picked: list[User] = []
    if rng.random() < 0.8:
        picked.append(admin)
    history_player: User = players[0]
    if with_history_player and history_player.id != admin.id:
        picked.append(history_player)
    others: list[User] = [
        player for player in players if player not in picked and player.id != admin.id
    ]
    picked += rng.sample(others, rng.randint(1, 5))
    taken: set[str] = {user.display_name.lower() for user in [admin, *picked]}
    guests: list[str] = [
        nickname
        for nickname in rng.sample(GUEST_NICKNAMES, rng.randint(0, 2))
        if nickname.lower() not in taken
    ]
    return [_Player(user=user, name=user.display_name) for user in picked] + [
        _Player(user=None, name=nickname) for nickname in guests
    ]


def _seat_in_new_room(
    rooms: RoomService, admin: User, template: Template, game_players: list[_Player]
) -> Room:
    """Une salle ouverte où les joueurs ont leur place : les comptes la rejoignent, les invités
    entrent avec leur pseudo."""
    room: Room = rooms.create(admin, template.id)
    for player in game_players:
        if player.user is None:
            room = rooms.join_as_guest(room.code, player.name, None).room
        elif player.user.id != admin.id:
            room = rooms.join(player.user, room.code)
    return room


def _closed_game(
    session: Session,
    room: Room | None,
    admin: User,
    snapshot: TemplateSnapshot,
    game_players: list[_Player],
    closed_at: datetime,
    rng: random.Random,
) -> Game:
    tiers: list[SnapshotTier] = sorted(snapshot.tiers, key=lambda tier: tier.position)
    item_order: ItemOrder = rng.choice(list(ItemOrder))
    tiles: list[SnapshotTile] = sorted(snapshot.tiles, key=lambda tile: tile.position)
    if item_order == ItemOrder.RANDOM:
        rng.shuffle(tiles)
    started_at: datetime = closed_at - timedelta(
        seconds=len(tiles) * ROUND_SECONDS + COOLDOWN_SECONDS
    )
    snapshot.taken_at = started_at
    admin_plays: bool = any(
        player.user is not None and player.user.id == admin.id for player in game_players
    )
    game: Game = Game(
        room_id=None if room is None else room.id,
        snapshot_id=snapshot.id,
        admin_id=admin.id,
        status=GameStatus.CLOSED,
        item_order=item_order,
        admin_plays=admin_plays,
        current_round_number=len(tiles),
        started_at=started_at,
        cooldown_ends_at=closed_at,
        closed_at=closed_at,
        public_token=generate_public_results_token(),
    )
    session.add(game)
    for number, tile in enumerate(tiles, start=1):
        round_start: datetime = started_at + timedelta(seconds=(number - 1) * ROUND_SECONDS)
        game.rounds.append(
            Round(
                number=number,
                snapshot_tile_id=tile.id,
                started_at=round_start,
                ended_at=round_start + timedelta(seconds=ROUND_SECONDS),
            )
        )
    # Les items que personne ne place, tirés une fois pour toute la partie
    nobody_places: set[uuid.UUID] = {tile.id for tile in tiles if rng.random() < NOBODY_PLACES_RATE}
    for player in game_players:
        frozen: GamePlayer = GamePlayer(
            user_id=None if player.user is None else player.user.id, display_name=player.name
        )
        game.players.append(frozen)
        _place_every_item(game, frozen, tiles, tiers, nobody_places, rng)
    return game


def _place_every_item(
    game: Game,
    player: GamePlayer,
    tiles: list[SnapshotTile],
    tiers: list[SnapshotTier],
    nobody_places: set[uuid.UUID],
    rng: random.Random,
) -> None:
    """Les placements d'un joueur : chaque item placé a un placement de tour et un placement
    final au même endroit (le cooldown les recopie) ; un item manqué n'a qu'un vote absent."""
    next_position: dict[uuid.UUID, int] = {}
    for tile in tiles:
        if tile.id in nobody_places or rng.random() < ABSENT_RATE:
            game.placements.append(
                Placement(player=player, snapshot_tile_id=tile.id, phase=PlacementPhase.ROUND)
            )
            continue
        # Plutôt les tiers du haut, comme de vrais joueurs
        tier: SnapshotTier = rng.choices(tiers, weights=range(len(tiers), 0, -1))[0]
        position: int = next_position.get(tier.id, 0)
        next_position[tier.id] = position + 1
        for phase in (PlacementPhase.ROUND, PlacementPhase.FINAL):
            game.placements.append(
                Placement(
                    player=player,
                    snapshot_tile_id=tile.id,
                    phase=phase,
                    snapshot_tier_id=tier.id,
                    position=position,
                )
            )
