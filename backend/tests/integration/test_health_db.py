import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_health_db_against_real_postgres(client: TestClient):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
