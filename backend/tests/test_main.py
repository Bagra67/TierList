from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.main import api_app, app

# Application racine, lancée par uvicorn : l'API y est servie sous /api
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    api_app.dependency_overrides.clear()


def test_health():
    # Aucune dépendance remplacée : la sonde de vie ne doit pas toucher la base
    response = client.get("/api/health")
    assert response.status_code == 200
    # APP_RELEASE n'est pas défini en tests : la valeur par défaut
    assert response.json() == {"status": "ok", "release": "dev"}


def test_health_db_ok():
    # SQLite en mémoire : vérifie le chemin nominal sans dépendre d'un PostgreSQL lancé
    engine = create_engine("sqlite://")

    def sqlite_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    api_app.dependency_overrides[get_db_session] = sqlite_session

    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "release": "dev"}


class UnreachableDatabaseSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_db_unavailable():
    api_app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response = client.get("/api/health/db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable", "code": "database_unavailable"}


def test_unknown_api_route_is_a_json_404():
    # Jamais index.html : un appel d'API inconnu doit échouer clairement
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "http_error"


def test_api_routes_are_only_served_under_the_prefix():
    assert client.get("/health").status_code == 404
