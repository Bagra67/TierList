import pytest
from fastapi.testclient import TestClient

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration


def test_health_db_against_real_postgres(client: TestClient):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
