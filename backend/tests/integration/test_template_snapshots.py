import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.exceptions.templates import TemplateHasNoTilesError, TemplateNotFoundError
from app.models.image import Image
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.services.templates import TemplateService

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(db_session: Session) -> User:
    user: User = User(email="alice@example.com", display_name="Alice")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def service(db_session: Session) -> TemplateService:
    return TemplateService(db_session, get_settings())


def create_image(db_session: Session, owner: User) -> Image:
    image: Image = Image(
        owner_id=owner.id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
    )
    db_session.add(image)
    db_session.flush()
    return image


def create_template(db_session: Session, service: TemplateService, owner: User) -> Template:
    """Template « Food » avec ses tiers par défaut, une tuile texte et une tuile image."""
    template: Template = service.create(owner, "Food")
    image: Image = create_image(db_session, owner)
    service.add_tile(owner, template.id, "Pizza", None)
    service.add_tile(owner, template.id, None, image.id)
    return template


def snapshot_tiers(snapshot: TemplateSnapshot) -> list[tuple[str, str, int]]:
    return [(tier.name, tier.color, tier.position) for tier in snapshot.tiers]


def snapshot_tiles(snapshot: TemplateSnapshot) -> list[tuple[str | None, uuid.UUID | None, int]]:
    return [(tile.text, tile.image_id, tile.position) for tile in snapshot.tiles]


def test_snapshot_copies_the_tiers_and_tiles(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)

    snapshot: TemplateSnapshot = service.take_snapshot(alice, template.id)

    assert snapshot.template_id == template.id
    assert snapshot.name == "Food"
    assert snapshot.taken_at is not None
    assert snapshot_tiers(snapshot) == [
        (tier.name, tier.color, tier.position) for tier in template.tiers
    ]
    assert snapshot_tiles(snapshot) == [
        ("Pizza", None, 0),
        (None, template.tiles[1].image_id, 1),
    ]


def test_editing_the_template_does_not_change_the_snapshot(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)
    snapshot: TemplateSnapshot = service.take_snapshot(alice, template.id)
    db_session.commit()
    tiers_before: list[tuple[str, str, int]] = snapshot_tiers(snapshot)
    tiles_before: list[tuple[str | None, uuid.UUID | None, int]] = snapshot_tiles(snapshot)

    service.rename(alice, template.id, "Drinks")
    service.update_tier(alice, template.id, template.tiers[0].id, {"name": "Top"})
    service.delete_tier(alice, template.id, template.tiers[-1].id)
    service.update_tile(alice, template.id, template.tiles[0].id, {"text": "Burger"})
    service.delete_tile(alice, template.id, template.tiles[1].id)
    service.add_tile(alice, template.id, "Sushi", None)
    db_session.expire_all()

    assert snapshot.name == "Food"
    assert snapshot_tiers(snapshot) == tiers_before
    assert snapshot_tiles(snapshot) == tiles_before


def test_a_deleted_template_cannot_be_snapshotted(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)
    service.delete(alice, template.id)

    with pytest.raises(TemplateNotFoundError):
        service.take_snapshot(alice, template.id)


def test_the_template_of_another_user_cannot_be_snapshotted(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)
    bob: User = User(email="bob@example.com", display_name="Bob")
    db_session.add(bob)
    db_session.flush()

    with pytest.raises(TemplateNotFoundError):
        service.take_snapshot(bob, template.id)


def test_a_template_without_tiles_cannot_be_snapshotted(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = service.create(alice, "Empty")

    with pytest.raises(TemplateHasNoTilesError):
        service.take_snapshot(alice, template.id)
    assert db_session.scalars(select(TemplateSnapshot)).all() == []


def test_the_snapshot_outlives_the_purge_of_its_template(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)
    snapshot: TemplateSnapshot = service.take_snapshot(alice, template.id)
    db_session.commit()
    service.delete(alice, template.id)
    template.deleted_at = datetime.now(UTC) - timedelta(days=31)
    db_session.flush()
    purge_settings = get_settings().model_copy(update={"deleted_template_retention_days": 30})

    purged_count: int = TemplateService(db_session, purge_settings).purge_deleted()
    db_session.refresh(snapshot)

    assert purged_count == 1
    assert snapshot.template_id is None
    assert len(snapshot.tiers) == 6
    assert len(snapshot.tiles) == 2


def test_the_snapshot_outlives_the_deletion_of_the_account(
    db_session: Session, service: TemplateService, alice: User
):
    template: Template = create_template(db_session, service, alice)
    snapshot: TemplateSnapshot = service.take_snapshot(alice, template.id)
    db_session.commit()

    db_session.delete(alice)
    db_session.flush()
    db_session.refresh(snapshot)

    assert snapshot.template_id is None
    assert len(snapshot.tiles) == 2
