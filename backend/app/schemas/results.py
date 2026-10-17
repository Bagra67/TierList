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
    # Un nombre par tier, dans l'ordre des tiers (de haut en bas)
    votes_per_tier: list[int]
    # Toujours 0 sans les votes absents
    absent_count: int
    # Tier du classement médian ; None si aucun vote n'est compté (item non classé)
    median_tier_id: uuid.UUID | None


class PlayerResultsResponse(BaseModel):
    """Le classement final d'un joueur."""

    display_name: str
    # Un élément par tier, de haut en bas ; un tier peut être vide
    tiers: list[TierItemsResponse]
    # Items qu'il n'a jamais placés (absent, non rattrapé), dans l'ordre du template
    unplaced_item_ids: list[uuid.UUID]


class GameResultsResponse(BaseModel):
    """Résultats d'une partie close (US-5.2), lus par son lien (US-5.3)."""

    template_name: str
    closed_at: datetime
    include_absent_votes: bool
    # Tiers de la version figée, de haut en bas
    tiers: list[GameTierResponse]
    # Items de la partie, dans l'ordre du template
    items: list[CurrentItemResponse]
    # Classement médian : un élément par tier, de haut en bas
    median_ranking: list[TierItemsResponse]
    # Items sans aucun vote compté, dans l'ordre du template
    unranked_item_ids: list[uuid.UUID]
    # Un élément par item, dans l'ordre du template
    distribution: list[ItemDistributionResponse]
    # Les joueurs ; le room admin qui ne joue pas n'en fait pas partie
    players: list[PlayerResultsResponse]
