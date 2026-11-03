import os
import uuid
from collections.abc import Callable, Iterator
from contextlib import nullcontext
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from alembic import command
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_email_sender,
    get_image_storage,
    get_room_event_publisher,
    get_round_scheduler,
    get_session_factory,
)
from app.constants.api import API_PREFIX
from app.constants.error_codes import ErrorCode
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.main import api_app, app
from app.schemas.room_events import RoomEvent
from app.services.email import Email, EmailSender
from app.services.image_storage import ImageStorage, create_image_storage, quarantine_key
from tests.integration.helpers import alembic_config


def _service_unavailable(reason: str) -> None:
    # En CI, un service injoignable (base, stockage S3) est une erreur : on ne masque jamais un
    # test d'intégration.
    if os.environ.get("CI") == "true":
        pytest.fail(reason)
    pytest.skip(reason)


def _test_database_url(suffix: str) -> URL:
    try:
        settings = get_settings()
    except ValidationError:
        _service_unavailable("PostgreSQL settings missing: copy backend/.env.example to .env")
        raise

    test_database: str = f"{settings.postgres_db}{suffix}"
    xdist_worker: str | None = os.environ.get("PYTEST_XDIST_WORKER")
    if xdist_worker is not None:
        test_database = f"{test_database}_{xdist_worker}"
    admin_engine = create_engine(
        settings.database_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": test_database},
            ).scalar()
            if exists is None:
                quoted_name = connection.dialect.identifier_preparer.quote(test_database)
                connection.execute(text(f"CREATE DATABASE {quoted_name}"))
    except OperationalError:
        _service_unavailable(
            "PostgreSQL is not reachable: start it with `docker compose up -d --wait`"
        )
        raise
    finally:
        admin_engine.dispose()

    return settings.database_url.set(database=test_database)


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    return _test_database_url("_test")


@pytest.fixture(scope="session")
def migrations_database_url() -> URL:
    return _test_database_url("_test_migrations")


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: URL) -> Iterator[Engine]:
    command.upgrade(alembic_config(test_database_url), "head")

    connect_timeout = get_settings().database_connect_timeout_seconds
    engine = create_engine(test_database_url, connect_args={"connect_timeout": connect_timeout})
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture(scope="session")
def s3_image_storage() -> ImageStorage:
    settings: Settings = get_settings()
    storage: ImageStorage = create_image_storage(settings)
    try:
        storage.delete("connectivity-check")
    except BotoCoreError, ClientError:
        _service_unavailable(
            "S3 image storage is not reachable: start it with `docker compose up -d --wait` "
            "and set the IMAGE_S3_* settings (backend/.env.example)"
        )
        raise
    return storage


class FakeEmailSender(EmailSender):
    def __init__(self, sent: list[Email]) -> None:
        self.sent = sent

    def send(self, email: Email) -> None:
        self.sent.append(email)


@pytest.fixture
def sent_emails() -> list[Email]:
    return []


FAKE_IMAGE_BASE_URL = "https://images.example.com"
FAKE_PRESIGNED_BASE_URL = "https://signed.example.com"


class FakeImageStorage(ImageStorage):
    def __init__(self, stored: dict[str, bytes]) -> None:
        super().__init__(client=MagicMock(), bucket="fake", public_base_url=FAKE_IMAGE_BASE_URL)
        self.stored = stored

    def save(self, key: str, data: bytes) -> None:
        self.stored[key] = data

    def delete(self, key: str) -> None:
        self.stored.pop(key, None)

    def copy_to_quarantine(self, key: str) -> None:
        self.stored[quarantine_key(key)] = self.stored[key]

    def copy_from_quarantine(self, key: str) -> None:
        self.stored[key] = self.stored[quarantine_key(key)]

    def presigned_url(self, key: str) -> str:
        return f"{FAKE_PRESIGNED_BASE_URL}/{key}"


class FailingImageStorage(FakeImageStorage):
    def __init__(self, stored: dict[str, bytes], failing_key: str | None = None) -> None:
        super().__init__(stored)
        self.failing_key = failing_key

    def delete(self, key: str) -> None:
        if self.failing_key is None or key == self.failing_key:
            raise ClientError({"Error": {"Code": "InternalError"}}, "DeleteObject")
        super().delete(key)


@pytest.fixture
def stored_images() -> dict[str, bytes]:
    return {}


@pytest.fixture
def client(
    db_session: Session, sent_emails: list[Email], stored_images: dict[str, bytes]
) -> Iterator[TestClient]:
    email_sender = FakeEmailSender(sent_emails)
    image_storage: FakeImageStorage = FakeImageStorage(stored_images)
    api_app.dependency_overrides[get_db_session] = lambda: db_session
    api_app.dependency_overrides[get_email_sender] = lambda: email_sender
    api_app.dependency_overrides[get_image_storage] = lambda: image_storage
    api_app.dependency_overrides[get_session_factory] = lambda: lambda: nullcontext(db_session)
    try:
        yield TestClient(app, base_url=f"http://testserver{API_PREFIX}")
    finally:
        api_app.dependency_overrides.pop(get_db_session, None)
        api_app.dependency_overrides.pop(get_email_sender, None)
        api_app.dependency_overrides.pop(get_image_storage, None)
        api_app.dependency_overrides.pop(get_session_factory, None)


def http_test_settings() -> Settings:
    return get_settings().model_copy(update={"auth_cookie_secure": False})


@pytest.fixture
def auth_client(client: TestClient) -> Iterator[TestClient]:
    api_app.dependency_overrides[get_settings] = http_test_settings
    try:
        yield client
    finally:
        api_app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def override_settings(auth_client: TestClient) -> Callable[..., None]:

    def apply(**changes: object) -> None:
        api_app.dependency_overrides[get_settings] = lambda: http_test_settings().model_copy(
            update=changes
        )

    return apply


class RecordingRoomEventPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[uuid.UUID, RoomEvent]] = []
        self.disconnections: list[tuple[uuid.UUID, int]] = []
        self.closed_rooms: list[uuid.UUID] = []

    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        self.events.append((room_id, event))

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        self.disconnections.append((participant_id, close_code))

    def close_room(self, room_id: uuid.UUID) -> None:
        self.closed_rooms.append(room_id)

    def types(self) -> list[str]:
        return [event.type for _, event in self.events]


@pytest.fixture
def room_events(client: TestClient) -> Iterator[RecordingRoomEventPublisher]:
    publisher: RecordingRoomEventPublisher = RecordingRoomEventPublisher()
    api_app.dependency_overrides[get_room_event_publisher] = lambda: publisher
    try:
        yield publisher
    finally:
        api_app.dependency_overrides.pop(get_room_event_publisher, None)


class RecordingRoundScheduler:
    def __init__(self) -> None:
        self.deadlines: list[tuple[uuid.UUID, int, datetime]] = []
        self.cooldown_ends: list[tuple[uuid.UUID, datetime]] = []

    def schedule(self, game_id: uuid.UUID, round_number: int, ends_at: datetime) -> None:
        self.deadlines.append((game_id, round_number, ends_at))

    def schedule_cooldown_end(self, game_id: uuid.UUID, ends_at: datetime) -> None:
        self.cooldown_ends.append((game_id, ends_at))


@pytest.fixture
def round_scheduler(client: TestClient) -> Iterator[RecordingRoundScheduler]:
    scheduler: RecordingRoundScheduler = RecordingRoundScheduler()
    api_app.dependency_overrides[get_round_scheduler] = lambda: scheduler
    try:
        yield scheduler
    finally:
        api_app.dependency_overrides.pop(get_round_scheduler, None)
