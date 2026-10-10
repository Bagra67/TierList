import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.image import Image, ImageStatus
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.services.images import ImageService
from tests.integration.conftest import FakeImageStorage

pytestmark = pytest.mark.integration


def settings_with_retention(days: int) -> Settings:
    return get_settings().model_copy(update={"unused_image_retention_days": days})


@pytest.fixture
def alice(db_session: Session) -> User:
    user: User = User(email="alice@example.com", display_name="Alice")
    db_session.add(user)
    db_session.flush()
    return user


def create_image(
    db_session: Session,
    stored_images: dict[str, bytes],
    owner: User | None,
    created_days_ago: int,
    status: ImageStatus = ImageStatus.VISIBLE,
) -> Image:
    """Image envoyée il y a created_days_ago jours, avec son fichier dans le stockage factice."""
    image: Image = Image(
        owner_id=owner.id if owner is not None else None,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
        status=status,
        created_at=datetime.now(UTC) - timedelta(days=created_days_ago),
    )
    db_session.add(image)
    db_session.flush()
    stored_images[image.storage_key] = b"webp"
    return image


def use_in_a_tile(db_session: Session, owner: User, image: Image) -> None:
    template: Template = Template(owner_id=owner.id, name="Food")
    template.tiles.append(Tile(text=None, image_id=image.id, position=0))
    db_session.add(template)
    db_session.flush()


def stored_image_ids(db_session: Session) -> set[uuid.UUID]:
    return set(db_session.scalars(select(Image.id)).all())


def test_purge_erases_the_unused_images_older_than_the_retention(
    db_session: Session, stored_images: dict[str, bytes], alice: User
):
    old_unused: Image = create_image(db_session, stored_images, alice, created_days_ago=8)
    recent_unused: Image = create_image(db_session, stored_images, alice, created_days_ago=6)
    old_used: Image = create_image(db_session, stored_images, alice, created_days_ago=30)
    use_in_a_tile(db_session, alice, old_used)
    # Lues avant la purge : l'image supprimée ne peut plus être rechargée ensuite
    kept_ids: set[uuid.UUID] = {recent_unused.id, old_used.id}
    kept_keys: set[str] = {recent_unused.storage_key, old_used.storage_key}
    purged_key: str = old_unused.storage_key
    service: ImageService = ImageService(
        db_session, settings_with_retention(7), FakeImageStorage(stored_images)
    )

    purged_count: int = service.purge_unused()

    assert purged_count == 1
    assert stored_image_ids(db_session) == kept_ids
    assert set(stored_images) == kept_keys
    assert purged_key not in stored_images


def test_purge_erases_the_images_of_a_deleted_account(
    db_session: Session, stored_images: dict[str, bytes], alice: User
):
    image: Image = create_image(db_session, stored_images, alice, created_days_ago=8)
    db_session.delete(alice)
    db_session.flush()
    db_session.refresh(image)
    assert image.owner_id is None

    purged_count: int = ImageService(
        db_session, settings_with_retention(7), FakeImageStorage(stored_images)
    ).purge_unused()

    assert purged_count == 1
    assert stored_images == {}


def test_purge_keeps_the_images_handled_by_the_moderation(
    db_session: Session, stored_images: dict[str, bytes], alice: User
):
    for status in (ImageStatus.HIDDEN, ImageStatus.DELETED):
        create_image(db_session, stored_images, alice, created_days_ago=30, status=status)

    purged_count: int = ImageService(
        db_session, settings_with_retention(7), FakeImageStorage(stored_images)
    ).purge_unused()

    assert purged_count == 0
    assert len(stored_image_ids(db_session)) == 2


def test_purge_retention_is_configurable(
    db_session: Session, stored_images: dict[str, bytes], alice: User
):
    create_image(db_session, stored_images, alice, created_days_ago=10)
    storage: FakeImageStorage = FakeImageStorage(stored_images)

    kept_count: int = ImageService(db_session, settings_with_retention(30), storage).purge_unused()
    purged_count: int = ImageService(db_session, settings_with_retention(7), storage).purge_unused()

    assert kept_count == 0
    assert purged_count == 1


class FailingImageStorage(FakeImageStorage):
    """Stockage qui refuse d'effacer une clé donnée, comme un fournisseur S3 en panne."""

    def __init__(self, stored: dict[str, bytes], failing_key: str) -> None:
        super().__init__(stored)
        self.failing_key = failing_key

    def delete(self, key: str) -> None:
        if key == self.failing_key:
            raise ClientError({"Error": {"Code": "InternalError"}}, "DeleteObject")
        super().delete(key)


def test_a_file_that_cannot_be_erased_is_logged_and_the_others_are_still_erased(
    db_session: Session,
    stored_images: dict[str, bytes],
    alice: User,
    caplog: pytest.LogCaptureFixture,
):
    failing_key: str = create_image(
        db_session, stored_images, alice, created_days_ago=8
    ).storage_key
    create_image(db_session, stored_images, alice, created_days_ago=8)
    storage: FailingImageStorage = FailingImageStorage(stored_images, failing_key)

    with caplog.at_level(logging.ERROR):
        purged_count: int = ImageService(
            db_session, settings_with_retention(7), storage
        ).purge_unused()

    assert purged_count == 2
    assert stored_image_ids(db_session) == set()
    # Seul le fichier en échec reste, et sa clé est journalisée pour l'effacer à la main
    assert set(stored_images) == {failing_key}
    assert failing_key in caplog.text
