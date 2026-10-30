"""Réponse des résultats d'une partie close (docs/technical/results.md)."""

import uuid

from app.api.presenters.items import item_response, tier_response
from app.models.snapshot_tier import SnapshotTier
from app.schemas.results import (
    GameResultsResponse,
    ItemDistributionResponse,
    PlayerResultsResponse,
    TierItemsResponse,
)
from app.services.game_results import ClosedGameResults, PlayerBoard
from app.services.image_storage import ImageStorage
from app.services.results import ItemResults


def game_results_response(closed: ClosedGameResults, storage: ImageStorage) -> GameResultsResponse:
    tiers: list[SnapshotTier] = list(closed.game.snapshot.tiers)
    distribution: list[ItemDistributionResponse] = []
    for tile in closed.game.snapshot.tiles:
        item: ItemResults = closed.results.items[tile.id]
        median_tier_id: uuid.UUID | None = (
            tiers[item.median_tier_index].id if item.median_tier_index is not None else None
        )
        distribution.append(
            ItemDistributionResponse(
                item_id=tile.id,
                votes_per_tier=list(item.votes_per_tier),
                absent_count=item.absent_count,
                player_indexes_per_tier=[list(voters) for voters in item.voters_per_tier],
                absent_player_indexes=list(item.absent_player_indexes),
                median_tier_id=median_tier_id,
            )
        )
    return GameResultsResponse(
        template_name=closed.game.snapshot.name,
        closed_at=closed.closed_at,
        include_absent_votes=closed.include_absent_votes,
        tiers=[tier_response(tier) for tier in tiers],
        items=[item_response(tile, storage) for tile in closed.game.snapshot.tiles],
        median_ranking=_tier_items(tiers, closed.results.median_ranking),
        unranked_item_ids=list(closed.results.unranked_tile_ids),
        distribution=distribution,
        players=[_player_response(tiers, board) for board in closed.boards],
    )


def _tier_items(
    tiers: list[SnapshotTier], items_per_tier: tuple[tuple[uuid.UUID, ...], ...]
) -> list[TierItemsResponse]:
    return [
        TierItemsResponse(tier_id=tier.id, item_ids=list(item_ids))
        for tier, item_ids in zip(tiers, items_per_tier, strict=True)
    ]


def _player_response(tiers: list[SnapshotTier], board: PlayerBoard) -> PlayerResultsResponse:
    return PlayerResultsResponse(
        display_name=board.player.display_name,
        tiers=_tier_items(tiers, board.tiers),
        unplaced_item_ids=list(board.unplaced_tile_ids),
    )
