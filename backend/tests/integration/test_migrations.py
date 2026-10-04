import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import URL, Engine, create_engine

import app.models  # noqa: F401  (enregistre les modèles dans Base.metadata)
from app.db.base import Base
from tests.integration.helpers import alembic_config

pytestmark = pytest.mark.integration


def _schema_differences(engine: Engine) -> list[object]:
    """Différences entre le schéma de la base et les modèles, comme les verrait --autogenerate."""
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


def test_migrations_match_the_models(migrated_engine: Engine):
    assert _schema_differences(migrated_engine) == []


def test_migrations_downgrade_and_upgrade_again(migrations_database_url: URL):
    config = alembic_config(migrations_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(migrations_database_url)
    try:
        assert _schema_differences(engine) == []
    finally:
        engine.dispose()
