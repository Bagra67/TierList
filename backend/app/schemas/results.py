import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.rooms import CurrentItemResponse, GameTierResponse


class TierItemsResponse(BaseModel):
    """Les items d'un tier, dans l'ordre."""

    tier_id: uuid.UUID
    item_ids: list[uuid.UUID]


class ItemDistributionResponse(BaseModel):
    """Vue globale d'un item : combien de joueurs l'ont mis dans chaque tier, et d'absents."""

    item_id: uuid.UUID
    votes_per_tier: list[int]
    absent_count: int
    player_indexes_per_tier: list[list[int]] | None
    absent_player_indexes: list[int] | None
    median_tier_id: uuid.UUID | None


class PlayerResultsResponse(BaseModel):
    """Le classement final d'un joueur."""

    display_name: str
    tiers: list[TierItemsResponse]
    # Items qu'il n'a jamais placés (absent, non rattrapé), dans l'ordre du template
    unplaced_item_ids: list[uuid.UUID]


class GameResultsResponse(BaseModel):
    """Résultats d'une partie close (US-5.2), lus par son lien (US-5.3)."""

    template_name: str
    closed_at: datetime
    include_absent_votes: bool
    tiers: list[GameTierResponse]
    # Items de la partie, dans l'ordre du template
    items: list[CurrentItemResponse]
    median_ranking: list[TierItemsResponse]
    # Items sans aucun vote compté, dans l'ordre du template
    unranked_item_ids: list[uuid.UUID]
    # Un élément par item, dans l'ordre du template
    distribution: list[ItemDistributionResponse]
    players: list[PlayerResultsResponse]
