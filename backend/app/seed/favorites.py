import logging
import random
import uuid

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.template_favorite import TemplateFavorite
from app.seed.other_players import pick_other_players_per_template

logger = logging.getLogger(__name__)


def favorite_public_templates(
    session: Session,
    player_ids: list[uuid.UUID],
    template_ids: list[uuid.UUID],
    max_favorites_per_template: int,
    rng: random.Random,
) -> int:
    favorites: list[dict[str, uuid.UUID]] = pick_other_players_per_template(
        session, player_ids, template_ids, max_favorites_per_template, rng
    )
    if favorites:
        session.execute(insert(TemplateFavorite), favorites)
    logger.info("Favoris : %d sur %d modèles publics", len(favorites), len(template_ids))
    return len(favorites)
