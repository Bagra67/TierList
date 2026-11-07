import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class FinalPlacement:
    tier_index: int
    position: int


@dataclass(frozen=True)
class PlayerRanking:
    final_placements: Mapping[uuid.UUID, FinalPlacement]
    absent_tile_ids: frozenset[uuid.UUID]


@dataclass(frozen=True)
class ItemResults:
    votes_per_tier: tuple[int, ...]
    absent_count: int
    voters_per_tier: tuple[tuple[int, ...], ...]
    absent_player_indexes: tuple[int, ...]
    median_score: Fraction | None
    mean_score: Fraction | None
    median_tier_index: int | None


@dataclass(frozen=True)
class GameResults:
    items: Mapping[uuid.UUID, ItemResults]
    median_ranking: tuple[tuple[uuid.UUID, ...], ...]
    unranked_tile_ids: tuple[uuid.UUID, ...]


def compute_results(
    tier_count: int,
    tile_ids: Sequence[uuid.UUID],
    players: Sequence[PlayerRanking],
    include_absent_votes: bool,
) -> GameResults:
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
    voters_per_tier: list[list[int]] = [[] for _ in range(tier_count)]
    absent_player_indexes: list[int] = []
    scores: list[Fraction] = []
    for player_index, (player, player_scores) in enumerate(
        zip(players, scores_per_player, strict=True)
    ):
        if not include_absent_votes and tile_id in player.absent_tile_ids:
            continue
        placement: FinalPlacement | None = player.final_placements.get(tile_id)
        if placement is None:
            if include_absent_votes:
                absent_player_indexes.append(player_index)
            continue
        voters_per_tier[placement.tier_index].append(player_index)
        scores.append(player_scores[tile_id])

    votes_per_tier: tuple[int, ...] = tuple(len(voters) for voters in voters_per_tier)
    voters: tuple[tuple[int, ...], ...] = tuple(tuple(voters) for voters in voters_per_tier)
    if not scores:
        return ItemResults(
            votes_per_tier=votes_per_tier,
            absent_count=len(absent_player_indexes),
            voters_per_tier=voters,
            absent_player_indexes=tuple(absent_player_indexes),
            median_score=None,
            mean_score=None,
            median_tier_index=None,
        )
    median_score: Fraction = _median_score(scores)
    mean_score: Fraction = sum(scores, Fraction(0)) / len(scores)
    return ItemResults(
        votes_per_tier=votes_per_tier,
        absent_count=len(absent_player_indexes),
        voters_per_tier=voters,
        absent_player_indexes=tuple(absent_player_indexes),
        median_score=median_score,
        mean_score=mean_score,
        median_tier_index=math.floor(median_score),
    )


def _median_score(scores: Sequence[Fraction]) -> Fraction:
    sorted_scores: list[Fraction] = sorted(scores)
    return sorted_scores[len(sorted_scores) // 2]


def _median_ranking(
    tier_count: int,
    tile_ids: Sequence[uuid.UUID],
    items: Mapping[uuid.UUID, ItemResults],
) -> tuple[tuple[uuid.UUID, ...], ...]:
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
