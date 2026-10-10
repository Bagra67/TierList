import os
from collections.abc import Callable, Iterator
from unittest.mock import MagicMock

import pytest
from alembic import command
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_email_sender, get_image_storage
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.main import app
from app.services.email import Email, EmailSender
from app.services.image_storage import ImageStorage, create_image_storage
from tests.integration.helpers import alembic_config


def _service_unavailable(reason: str) -> None:
    # En CI, un service injoignable (base, stockage S3) est une erreur : on ne masque jamais un
    # test d'intégration.
    if os.environ.get("CI") == "true":
        pytest.fail(reason)
    pytest.skip(reason)


def _test_database_url(suffix: str) -> URL:
    """URL de la base `<POSTGRES_DB><suffix>`, créée si besoin (jamais la base de dev)."""
    try:
        settings = get_settings()
    except ValidationError:
        _service_unavailable("PostgreSQL settings missing: copy backend/.env.example to .env")
        raise

    test_database = f"{settings.postgres_db}{suffix}"
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
    """URL de la base de test `<POSTGRES_DB>_test`, partagée par les tests d'intégration."""
    return _test_database_url("_test")


@pytest.fixture(scope="session")
def migrations_database_url() -> URL:
    """URL de la base `<POSTGRES_DB>_test_migrations`, réservée aux tests qui descendent les
    migrations : la base de test partagée garde son schéma pendant toute la session."""
    return _test_database_url("_test_migrations")


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: URL) -> Iterator[Engine]:
    """Applique les migrations Alembic sur la base de test, puis fournit un engine."""
    command.upgrade(alembic_config(test_database_url), "head")

    connect_timeout = get_settings().database_connect_timeout_seconds
    engine = create_engine(test_database_url, connect_args={"connect_timeout": connect_timeout})
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """Session isolée : tout ce qu'un test écrit est annulé à la fin du test."""
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
    """Vrai stockage des images, configuré par les réglages IMAGE_S3_* (SeaweedFS en local et en
    CI) : seuls les tests du stockage l'utilisent, les tests d'API ont FakeImageStorage."""
    settings: Settings = get_settings()
    storage: ImageStorage = create_image_storage(settings)
    try:
        # Supprimer une clé absente ne fait rien, mais vérifie l'adresse, les clés et le bucket
        storage.delete("connectivity-check")
    except (BotoCoreError, ClientError):
        _service_unavailable(
            "S3 image storage is not reachable: start it with `docker compose up -d --wait` "
            "and set the IMAGE_S3_* settings (backend/.env.example)"
        )
        raise
    return storage


class FakeEmailSender(EmailSender):
    """Garde les emails au lieu de les envoyer : aucun test ne contacte un serveur SMTP."""

    def __init__(self, sent: list[Email]) -> None:
        self.sent = sent

    def send(self, email: Email) -> None:
        self.sent.append(email)


@pytest.fixture
def sent_emails() -> list[Email]:
    """Emails « envoyés » pendant le test (les tâches de fond s'exécutent avant la réponse)."""
    return []


FAKE_IMAGE_BASE_URL = "https://images.example.com"


class FakeImageStorage(ImageStorage):
    """Garde les images en mémoire : les tests d'API ne contactent pas le stockage S3 (le vrai
    stockage est testé par test_image_storage.py)."""

    def __init__(self, stored: dict[str, bytes]) -> None:
        super().__init__(client=MagicMock(), bucket="fake", public_base_url=FAKE_IMAGE_BASE_URL)
        self.stored = stored

    def save(self, key: str, data: bytes) -> None:
        self.stored[key] = data

    def delete(self, key: str) -> None:
        self.stored.pop(key, None)


@pytest.fixture
def stored_images() -> dict[str, bytes]:
    """Images « stockées » pendant le test, par clé de stockage."""
    return {}


@pytest.fixture
def client(
    db_session: Session, sent_emails: list[Email], stored_images: dict[str, bytes]
) -> Iterator[TestClient]:
    email_sender = FakeEmailSender(sent_emails)
    image_storage: FakeImageStorage = FakeImageStorage(stored_images)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    app.dependency_overrides[get_image_storage] = lambda: image_storage
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_email_sender, None)
        app.dependency_overrides.pop(get_image_storage, None)


def http_test_settings() -> Settings:
    # TestClient parle en HTTP à http://testserver/auth/... (sans le proxy /api) :
    # le cookie doit être non Secure et sur /auth pour que le client le renvoie.
    return get_settings().model_copy(
        update={"auth_cookie_secure": False, "auth_cookie_path": "/auth"}
    )


@pytest.fixture
def auth_client(client: TestClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = http_test_settings
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def override_settings(auth_client: TestClient) -> Callable[..., None]:
    """Change des réglages pour un test, ex. override_settings(password_min_length=12).

    Ne concerne que les réglages injectés par FastAPI (Depends(get_settings)) ; auth_client
    retire la surcharge à la fin du test.
    """

    def apply(**changes: object) -> None:
        app.dependency_overrides[get_settings] = lambda: http_test_settings().model_copy(
            update=changes
        )

    return apply
