"""Résultats d'une partie close, lus par son lien (US-5.2, US-5.3 ; docs/technical/results.md).

Le service lit la partie et ses joueurs figés, construit le classement de chaque joueur et
appelle le calcul pur (services/results.py). Seuls les joueurs comptent : le room admin qui ne
joue pas n'a aucun placement, donc aucun joueur figé.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.exceptions.games import GameResultsNotFoundError
from app.models.enums import PlacementPhase
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.placement import Placement
from app.repositories import games as game_repository
from app.services.results import FinalPlacement, GameResults, PlayerRanking, compute_results


@dataclass(frozen=True)
class PlayerBoard:
    """Le classement final d'un joueur, tel qu'il l'a laissé."""

    player: GamePlayer
    # Un tuple par tier, de haut en bas : ses items par position
    tiers: tuple[tuple[uuid.UUID, ...], ...]
    # Items qu'il n'a jamais placés (absent, non rattrapé), dans l'ordre du template
    unplaced_tile_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class ClosedGameResults:
    game: Game
    # Toujours rempli pour une partie close ; repris ici pour le typage
    closed_at: datetime
    include_absent_votes: bool
    results: GameResults
    boards: tuple[PlayerBoard, ...]


class GameResultsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def results(self, public_token: str, include_absent_votes: bool) -> ClosedGameResults:
        """Résultats de la partie close de ce lien, avec ou sans les votes absents (US-5.2).
        Recalculés à chaque lecture : 10 joueurs et 32 items au plus (results.md)."""
        game: Game | None = game_repository.get_closed_game_by_token(self._session, public_token)
        if game is None or game.closed_at is None:
            raise GameResultsNotFoundError
        tier_indexes: dict[uuid.UUID, int] = {
            tier.id: index for index, tier in enumerate(game.snapshot.tiers)
        }
        tile_ids: list[uuid.UUID] = [tile.id for tile in game.snapshot.tiles]
        placements_per_player: dict[uuid.UUID, list[Placement]] = {}
        for placement in game.placements:
            if placement.player_id is not None:
                placements_per_player.setdefault(placement.player_id, []).append(placement)

        rankings: list[PlayerRanking] = []
        boards: list[PlayerBoard] = []
        for player in game.players:
            ranking: PlayerRanking = _ranking_of(
                placements_per_player.get(player.id, []), tier_indexes
            )
            rankings.append(ranking)
            boards.append(_board_of(player, ranking, len(tier_indexes), tile_ids))
        results: GameResults = compute_results(
            len(tier_indexes), tile_ids, rankings, include_absent_votes
        )
        return ClosedGameResults(
            game=game,
            closed_at=game.closed_at,
            include_absent_votes=include_absent_votes,
            results=results,
            boards=tuple(boards),
        )


def _ranking_of(placements: list[Placement], tier_indexes: dict[uuid.UUID, int]) -> PlayerRanking:
    """Le classement d'un joueur pour le calcul : ses placements finaux et ses votes absents."""
    final_placements: dict[uuid.UUID, FinalPlacement] = {}
    absent_tile_ids: set[uuid.UUID] = set()
    for placement in placements:
        if placement.phase == PlacementPhase.ROUND and placement.is_absent:
            absent_tile_ids.add(placement.snapshot_tile_id)
        elif (
            placement.phase == PlacementPhase.FINAL
            and placement.snapshot_tier_id is not None
            and placement.position is not None
        ):
            final_placements[placement.snapshot_tile_id] = FinalPlacement(
                tier_index=tier_indexes[placement.snapshot_tier_id], position=placement.position
            )
    return PlayerRanking(
        final_placements=final_placements, absent_tile_ids=frozenset(absent_tile_ids)
    )


def _board_of(
    player: GamePlayer, ranking: PlayerRanking, tier_count: int, tile_ids: list[uuid.UUID]
) -> PlayerBoard:
    tiers: list[list[uuid.UUID]] = [[] for _ in range(tier_count)]
    ordered: list[tuple[uuid.UUID, FinalPlacement]] = sorted(
        ranking.final_placements.items(), key=lambda entry: entry[1].position
    )
    for tile_id, final_placement in ordered:
        tiers[final_placement.tier_index].append(tile_id)
    unplaced: tuple[uuid.UUID, ...] = tuple(
        tile_id for tile_id in tile_ids if tile_id not in ranking.final_placements
    )
    return PlayerBoard(
        player=player, tiers=tuple(tuple(tier) for tier in tiers), unplaced_tile_ids=unplaced
    )
