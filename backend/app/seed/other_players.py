import random
import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.template import Template


def pick_other_players_per_template(
    session: Session,
    player_ids: list[uuid.UUID],
    template_ids: list[uuid.UUID],
    max_players_per_template: int,
    rng: random.Random,
) -> list[dict[str, uuid.UUID]]:
    owners: Select[uuid.UUID, uuid.UUID] = select(Template.id, Template.owner_id).where(
        Template.id.in_(template_ids)
    )
    picks: list[dict[str, uuid.UUID]] = []
    for template_id, owner_id in session.execute(owners).all():
        others: list[uuid.UUID] = [player_id for player_id in player_ids if player_id != owner_id]
        pick_count: int = rng.randint(0, min(max_players_per_template, len(others)))
        picks.extend(
            {"template_id": template_id, "user_id": user_id}
            for user_id in rng.sample(others, pick_count)
        )
    return picks
