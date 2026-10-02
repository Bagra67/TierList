from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_item():
    response = client.post("/items/", json={"name": "Python", "tier": "S"})
    assert response.status_code == 201
    item = response.json()
    assert item["name"] == "Python"

    response = client.get(f"/items/{item['id']}")
    assert response.status_code == 200
    assert response.json() == item


def test_get_unknown_item():
    response = client.get("/items/9999")
    assert response.status_code == 404
