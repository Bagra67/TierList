import logging
import random
import uuid

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.template_like import TemplateLike
from app.seed.other_players import pick_other_players_per_template

logger = logging.getLogger(__name__)


def like_public_templates(
    session: Session,
    player_ids: list[uuid.UUID],
    template_ids: list[uuid.UUID],
    max_likes_per_template: int,
    rng: random.Random,
) -> int:
    likes: list[dict[str, uuid.UUID]] = pick_other_players_per_template(
        session, player_ids, template_ids, max_likes_per_template, rng
    )
    if likes:
        session.execute(insert(TemplateLike), likes)
    logger.info("J'aime : %d sur %d modèles publics", len(likes), len(template_ids))
    return len(likes)
