import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.rooms import CurrentItemResponse, GameTierResponse


class TierItemsResponse(BaseModel):
    """The items of a tier, in order."""

    tier_id: uuid.UUID
    item_ids: list[uuid.UUID]


class ItemDistributionResponse(BaseModel):
    """Overall view of an item: how many players put it in each tier, and how many were absent."""

    item_id: uuid.UUID
    votes_per_tier: list[int]
    absent_count: int
    player_indexes_per_tier: list[list[int]] | None
    absent_player_indexes: list[int] | None
    median_tier_id: uuid.UUID | None


class PlayerResultsResponse(BaseModel):
    """The final ranking of a player."""

    id: uuid.UUID
    display_name: str
    tiers: list[TierItemsResponse]
    unplaced_item_ids: list[uuid.UUID]


class GameResultsResponse(BaseModel):
    """Results of a closed game (US-5.2), read through its link (US-5.3)."""

    game_id: uuid.UUID
    template_name: str
    closed_at: datetime
    include_absent_votes: bool
    tiers: list[GameTierResponse]
    items: list[CurrentItemResponse]
    median_ranking: list[TierItemsResponse]
    unranked_item_ids: list[uuid.UUID]
    distribution: list[ItemDistributionResponse]
    players: list[PlayerResultsResponse]
