from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.main as main_module
from app.core.config import Settings, get_settings
from app.models.image import Image, ImageStatus
from app.models.template import Template
from app.models.user import User
from app.services.maintenance import purge_deleted_templates, purge_unused_images
from app.services.nightly_scheduler import nightly_scheduler
from tests.integration.conftest import FakeImageStorage

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(db_session: Session) -> User:
    user: User = User(email="alice@example.com", display_name="Alice")
    db_session.add(user)
    db_session.flush()
    return user


def test_purge_deleted_templates_uses_its_own_session_and_returns_the_count(
    db_session: Session, alice: User
):
    db_session.add_all(
        [
            Template(owner_id=alice.id, name="Old", deleted_at=datetime.now(UTC) - timedelta(31)),
            Template(owner_id=alice.id, name="Active"),
        ]
    )
    db_session.flush()

    retention_30_days: Settings = get_settings().model_copy(
        update={"deleted_template_retention_days": 30}
    )

    purged_count: int = purge_deleted_templates(lambda: nullcontext(db_session), retention_30_days)

    assert purged_count == 1
    assert db_session.scalars(select(Template.name)).all() == ["Active"]


def test_purge_unused_images_erases_the_files_and_returns_the_count(
    db_session: Session, stored_images: dict[str, bytes], alice: User
):
    image: Image = Image(
        owner_id=alice.id,
        storage_key="old.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
        status=ImageStatus.VISIBLE,
        created_at=datetime.now(UTC) - timedelta(days=8),
    )
    db_session.add(image)
    db_session.flush()
    stored_images["old.webp"] = b"webp"

    retention_7_days: Settings = get_settings().model_copy(
        update={"unused_image_retention_days": 7}
    )

    purged_count: int = purge_unused_images(
        lambda: nullcontext(db_session), retention_7_days, FakeImageStorage(stored_images)
    )

    assert purged_count == 1
    assert stored_images == {}


def test_the_nightly_tasks_start_with_the_app(client: TestClient):
    with client:
        assert nightly_scheduler.is_running
    assert not nightly_scheduler.is_running


def test_the_nightly_tasks_can_be_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    disabled: Settings = get_settings().model_copy(update={"maintenance_enabled": False})
    monkeypatch.setattr(main_module, "get_settings", lambda: disabled)

    with client:
        assert not nightly_scheduler.is_running
