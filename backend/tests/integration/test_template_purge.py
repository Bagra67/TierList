from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.template import Template
from app.models.tier import Tier
from app.models.tile import Tile
from app.models.user import User
from app.services.templates import TemplateService

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def settings_with_retention(days: int) -> Settings:
    return get_settings().model_copy(update={"deleted_template_retention_days": days})


def create_template(db_session: Session, name: str, deleted_days_ago: int | None) -> Template:
    """Template d'Alice avec ses tiers par défaut et une tuile ; supprimé il y a deleted_days_ago
    jours, ou actif si None."""
    alice = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    template = TemplateService(db_session, get_settings()).create(alice, name)
    template.tiles.append(Tile(text="Tile", position=0))
    if deleted_days_ago is not None:
        template.deleted_at = NOW - timedelta(days=deleted_days_ago)
    db_session.flush()
    return template


@pytest.fixture(autouse=True)
def alice(db_session: Session) -> None:
    db_session.add(User(email="alice@example.com", display_name="Alice"))
    db_session.flush()


def stored_template_names(db_session: Session) -> list[str]:
    return sorted(db_session.scalars(select(Template.name)).all())


def test_purge_deletes_templates_deleted_longer_than_the_retention(db_session: Session):
    create_template(db_session, "Old", deleted_days_ago=31)
    create_template(db_session, "Recent", deleted_days_ago=29)
    create_template(db_session, "Active", deleted_days_ago=None)

    purged_count = TemplateService(db_session, settings_with_retention(30)).purge_deleted(NOW)

    assert purged_count == 1
    assert stored_template_names(db_session) == ["Active", "Recent"]


def test_purge_also_deletes_the_tiers_and_tiles(db_session: Session):
    create_template(db_session, "Old", deleted_days_ago=31)

    TemplateService(db_session, settings_with_retention(30)).purge_deleted(NOW)

    assert db_session.scalars(select(Tier)).all() == []
    assert db_session.scalars(select(Tile)).all() == []


def test_purge_retention_is_configurable(db_session: Session):
    create_template(db_session, "Deleted 10 days ago", deleted_days_ago=10)

    kept_count = TemplateService(db_session, settings_with_retention(30)).purge_deleted(NOW)
    purged_count = TemplateService(db_session, settings_with_retention(7)).purge_deleted(NOW)

    assert kept_count == 0
    assert purged_count == 1
    assert stored_template_names(db_session) == []
