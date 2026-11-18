import logging
import random
import uuid

from sqlalchemy import Select, insert, select
from sqlalchemy.orm import Session

from app.models.template import Template
from app.models.template_like import TemplateLike

logger = logging.getLogger(__name__)


def like_public_templates(
    session: Session,
    player_ids: list[uuid.UUID],
    template_ids: list[uuid.UUID],
    max_likes_per_template: int,
    rng: random.Random,
) -> int:
    owners: Select[uuid.UUID, uuid.UUID] = select(Template.id, Template.owner_id).where(
        Template.id.in_(template_ids)
    )
    likes: list[dict[str, uuid.UUID]] = []
    for template_id, owner_id in session.execute(owners).all():
        others: list[uuid.UUID] = [player_id for player_id in player_ids if player_id != owner_id]
        like_count: int = rng.randint(0, min(max_likes_per_template, len(others)))
        likes.extend(
            {"template_id": template_id, "user_id": user_id}
            for user_id in rng.sample(others, like_count)
        )
    if likes:
        session.execute(insert(TemplateLike), likes)
    logger.info("J'aime : %d sur %d modèles publics", len(likes), len(template_ids))
    return len(likes)
