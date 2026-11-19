import uuid

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import URL, Engine, create_engine, text

import app.models  # noqa: F401  (enregistre les modèles dans Base.metadata)
from app.db.base import Base
from tests.integration.helpers import alembic_config

pytestmark = pytest.mark.integration


def _schema_differences(engine: Engine) -> list[object]:
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


def test_migrations_match_the_models(migrated_engine: Engine):
    differences = _schema_differences(migrated_engine)

    assert differences == [], f"Models and migrations differ, add a migration: {differences}"


def test_migrations_downgrade_and_upgrade_again(migrations_database_url: URL):
    config = alembic_config(migrations_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(migrations_database_url)
    try:
        differences = _schema_differences(engine)
    finally:
        engine.dispose()

    assert differences == [], f"Schema rebuilt by the migrations differs: {differences}"


def test_the_migration_copies_the_latest_moderation_deletion_reason_to_deleted_templates(
    migrations_database_url: URL,
):
    config = alembic_config(migrations_database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "3cc4d74966c1")
    owner_id, deleted_id, live_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    engine = create_engine(migrations_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO users (id, email, display_name) VALUES (:id, 'o@x.fr', 'O')"),
                {"id": owner_id},
            )
            connection.execute(
                text(
                    "INSERT INTO templates (id, owner_id, name, deleted_at) VALUES "
                    "(:deleted, :owner, 'Deleted', now()), (:live, :owner, 'Live', NULL)"
                ),
                {"deleted": deleted_id, "live": live_id, "owner": owner_id},
            )
            for target_id, reason, minutes_ago in (
                (deleted_id, "Old reason", 10),
                (deleted_id, "Latest reason", 1),
                (live_id, "Undone", 5),
            ):
                connection.execute(
                    text(
                        "INSERT INTO moderation_actions (id, created_at, actor_name, action, "
                        "target_type, target_id, target_label, reason) VALUES (:id, "
                        "now() - make_interval(mins => :minutes), 'Nina', 'delete', "
                        "'template', :target, 'T', :reason)"
                    ),
                    {
                        "id": uuid.uuid4(),
                        "minutes": minutes_ago,
                        "target": target_id,
                        "reason": reason,
                    },
                )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            reasons = dict(
                connection.execute(text("SELECT name, deletion_reason FROM templates")).all()
            )
    finally:
        engine.dispose()
    assert reasons == {"Deleted": "Latest reason", "Live": None}
