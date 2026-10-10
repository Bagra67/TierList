import threading
import time
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.exceptions.templates import LastTierError
from app.models.template import Template
from app.models.tier import Tier
from app.models.user import User
from app.repositories import templates as template_repository
from app.services.templates import TemplateService

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration

# Temps laissé à la seconde requête pour arriver jusqu'au verrou avant que la première se termine
SECOND_REQUEST_HEAD_START_SECONDS = 0.3


@pytest.fixture
def committed_template(migrated_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID]]:
    """Utilisateur et template de deux tiers réellement validés en base : deux requêtes
    simultanées utilisent deux connexions, ce que la session isolée des autres tests ne permet
    pas. Supprimés à la fin."""
    with Session(migrated_engine) as session:
        owner: User = User(email=f"lock-{uuid.uuid4()}@example.com", display_name="Lock")
        session.add(owner)
        session.flush()
        template: Template = TemplateService(session, get_settings()).create(owner, "Locked")
        # Deux tiers seulement : supprimer les deux en même temps viderait la tier list
        for extra_tier in template.tiers[2:]:
            session.delete(extra_tier)
        session.commit()
        owner_id: uuid.UUID = owner.id
        template_id: uuid.UUID = template.id
    try:
        yield owner_id, template_id
    finally:
        with Session(migrated_engine) as session:
            # Supprime aussi ses templates et leurs tiers (ON DELETE CASCADE)
            session.execute(delete(User).where(User.id == owner_id))
            session.commit()


def test_two_simultaneous_deletions_keep_the_last_tier(
    migrated_engine: Engine, committed_template: tuple[uuid.UUID, uuid.UUID]
):
    owner_id: uuid.UUID = committed_template[0]
    template_id: uuid.UUID = committed_template[1]
    errors: list[Exception] = []

    with Session(migrated_engine) as first_request:
        # Première requête : supprime le premier tier, sans avoir encore validé
        template: Template | None = template_repository.get_owned_template(
            first_request, template_id, owner_id, for_update=True
        )
        assert template is not None
        second_tier_id: uuid.UUID = template.tiers[1].id
        first_request.delete(template.tiers[0])
        first_request.flush()

        # Seconde requête, en parallèle : supprime l'autre tier
        def delete_second_tier() -> None:
            with Session(migrated_engine) as second_request:
                owner: User | None = second_request.get(User, owner_id)
                assert owner is not None
                try:
                    TemplateService(second_request, get_settings()).delete_tier(
                        owner, template_id, second_tier_id
                    )
                except LastTierError as error:
                    errors.append(error)

        second_request_thread: threading.Thread = threading.Thread(target=delete_second_tier)
        second_request_thread.start()
        time.sleep(SECOND_REQUEST_HEAD_START_SECONDS)
        first_request.commit()
        second_request_thread.join(timeout=10)

    # La seconde requête a attendu la première, puis a vu qu'il ne restait qu'un tier
    assert len(errors) == 1
    with Session(migrated_engine) as session:
        remaining: list[Tier] = list(
            session.scalars(select(Tier).where(Tier.template_id == template_id)).all()
        )
    assert [tier.id for tier in remaining] == [second_tier_id]
