"""Calcul des résultats d'une partie close (docs/technical/results.md) : répartition des votes par
tier, votes absents et classement médian.

Fonctions pures, sans base de données : l'appelant fournit les tiers du snapshot, l'ordre des
tuiles et le classement final de chaque joueur. L'admin qui ne joue pas n'est pas un joueur : il
n'est pas passé ici.
"""

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class FinalPlacement:
    # 0 = tier du haut, le meilleur
    tier_index: int
    # Seul l'ordre des positions dans un tier compte, pas leur valeur
    position: int


@dataclass(frozen=True)
class PlayerRanking:
    # Classement final du joueur ; une tuile jamais placée (absente, non rattrapée) n'y figure pas
    final_placements: Mapping[uuid.UUID, FinalPlacement]
    # Tuiles pour lesquelles le joueur a un vote absent au tour, rattrapées ou non au cooldown
    absent_tile_ids: frozenset[uuid.UUID]


@dataclass(frozen=True)
class ItemResults:
    votes_per_tier: tuple[int, ...]
    absent_count: int
    # None quand aucun vote n'est compté pour l'item : il n'est alors pas classé
    median_score: Fraction | None
    mean_score: Fraction | None
    median_tier_index: int | None


@dataclass(frozen=True)
class GameResults:
    items: Mapping[uuid.UUID, ItemResults]
    # Un tuple par tier du snapshot, de haut en bas ; un tier peut être vide
    median_ranking: tuple[tuple[uuid.UUID, ...], ...]
    unranked_tile_ids: tuple[uuid.UUID, ...]


def compute_results(
    tier_count: int,
    tile_ids: Sequence[uuid.UUID],
    players: Sequence[PlayerRanking],
    include_absent_votes: bool,
) -> GameResults:
    """Calcule les résultats ; tile_ids est dans l'ordre du template (dernier départage)."""
    scores_per_player: list[dict[uuid.UUID, Fraction]] = []
    for player in players:
        scores_per_player.append(_scores_of(player))

    items: dict[uuid.UUID, ItemResults] = {}
    for tile_id in tile_ids:
        items[tile_id] = _item_results(
            tile_id, tier_count, players, scores_per_player, include_absent_votes
        )

    median_ranking: tuple[tuple[uuid.UUID, ...], ...] = _median_ranking(tier_count, tile_ids, items)
    unranked_tile_ids: list[uuid.UUID] = []
    for tile_id in tile_ids:
        if items[tile_id].median_tier_index is None:
            unranked_tile_ids.append(tile_id)
    return GameResults(
        items=items,
        median_ranking=median_ranking,
        unranked_tile_ids=tuple(unranked_tile_ids),
    )


def _scores_of(player: PlayerRanking) -> dict[uuid.UUID, Fraction]:
    """Score fin de chaque tuile du joueur : t + (k + 1/2) / n, entre t et t + 1.

    t = indice du tier, k = rang de la tuile dans ce tier (0 = première), n = nombre de tuiles du
    joueur dans ce tier. Diviser par n rend comparables des joueurs dont les tiers n'ont pas la
    même taille.
    """
    tiles_per_tier: dict[int, list[tuple[int, uuid.UUID]]] = {}
    for tile_id, placement in player.final_placements.items():
        tiles_per_tier.setdefault(placement.tier_index, []).append((placement.position, tile_id))

    scores: dict[uuid.UUID, Fraction] = {}
    for tier_index, tiles in tiles_per_tier.items():
        tiles.sort()
        tile_count: int = len(tiles)
        for rank_in_tier, (_position, tile_id) in enumerate(tiles):
            scores[tile_id] = tier_index + Fraction(2 * rank_in_tier + 1, 2 * tile_count)
    return scores


def _item_results(
    tile_id: uuid.UUID,
    tier_count: int,
    players: Sequence[PlayerRanking],
    scores_per_player: Sequence[Mapping[uuid.UUID, Fraction]],
    include_absent_votes: bool,
) -> ItemResults:
    votes_per_tier: list[int] = [0] * tier_count
    absent_count: int = 0
    scores: list[Fraction] = []
    for player, player_scores in zip(players, scores_per_player, strict=True):
        # Sans les votes absents, seuls comptent les joueurs qui ont voté pendant le tour
        if not include_absent_votes and tile_id in player.absent_tile_ids:
            continue
        placement: FinalPlacement | None = player.final_placements.get(tile_id)
        if placement is None:
            absent_count += 1
            continue
        votes_per_tier[placement.tier_index] += 1
        scores.append(player_scores[tile_id])

    if not scores:
        return ItemResults(
            votes_per_tier=tuple(votes_per_tier),
            absent_count=absent_count,
            median_score=None,
            mean_score=None,
            median_tier_index=None,
        )
    median_score: Fraction = _median_score(scores)
    mean_score: Fraction = sum(scores, Fraction(0)) / len(scores)
    return ItemResults(
        votes_per_tier=tuple(votes_per_tier),
        absent_count=absent_count,
        median_score=median_score,
        mean_score=mean_score,
        median_tier_index=math.floor(median_score),
    )


def _median_score(scores: Sequence[Fraction]) -> Fraction:
    """Score du milieu ; pour un nombre pair de votes, le moins bon des deux du milieu.

    Une majorité stricte des joueurs a donc mis l'item à ce niveau ou mieux (jugement majoritaire).
    """
    sorted_scores: list[Fraction] = sorted(scores)
    return sorted_scores[len(sorted_scores) // 2]


def _median_ranking(
    tier_count: int,
    tile_ids: Sequence[uuid.UUID],
    items: Mapping[uuid.UUID, ItemResults],
) -> tuple[tuple[uuid.UUID, ...], ...]:
    """Tier list médiane : chaque item dans le tier de son score médian.

    Dans un tier : score médian, puis score moyen, puis ordre du template.
    """
    sort_keys_per_tier: list[list[tuple[Fraction, Fraction, int, uuid.UUID]]] = []
    for _tier_index in range(tier_count):
        sort_keys_per_tier.append([])

    for template_order, tile_id in enumerate(tile_ids):
        item: ItemResults = items[tile_id]
        if item.median_tier_index is None or item.median_score is None or item.mean_score is None:
            continue
        sort_keys_per_tier[item.median_tier_index].append(
            (item.median_score, item.mean_score, template_order, tile_id)
        )

    median_ranking: list[tuple[uuid.UUID, ...]] = []
    for sort_keys in sort_keys_per_tier:
        sort_keys.sort()
        tier_tile_ids: list[uuid.UUID] = []
        for _median, _mean, _template_order, tile_id in sort_keys:
            tier_tile_ids.append(tile_id)
        median_ranking.append(tuple(tier_tile_ids))
    return tuple(median_ranking)
