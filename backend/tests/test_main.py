from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_hello():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health():
    # Aucune dépendance remplacée : la sonde de vie ne doit pas toucher la base
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_ok():
    # SQLite en mémoire : vérifie le chemin nominal sans dépendre d'un PostgreSQL lancé
    engine = create_engine("sqlite://")

    def sqlite_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = sqlite_session

    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class UnreachableDatabaseSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_db_unavailable():
    app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response = client.get("/health/db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable", "code": "database_unavailable"}
