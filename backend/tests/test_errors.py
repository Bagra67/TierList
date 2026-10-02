import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    # Application dédiée : ajouter ces routes à app.main modifierait le contrat OpenAPI
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/items/{item_id}")
    def get_item(item_id: int, limit: int) -> dict[str, int]:
        return {"item_id": item_id, "limit": limit}

    @app.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="Introuvable")

    return app


client = TestClient(create_app(), raise_server_exceptions=False)


def test_unexpected_error_returns_generic_500(capsys: pytest.CaptureFixture[str]):
    configure_logging("INFO")

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erreur interne du serveur"}
    assert "secret internal detail" not in response.text

    stderr = capsys.readouterr().err
    assert "ERROR:" in stderr
    assert "app.core.errors - Erreur non gérée sur GET /boom" in stderr
    assert "RuntimeError: secret internal detail" in stderr


def test_validation_error_lists_invalid_fields():
    response = client.get("/items/abc")

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Requête invalide"
    fields = {error["field"] for error in body["errors"]}
    assert fields == {"path.item_id", "query.limit"}
    assert all(error["message"] for error in body["errors"])


def test_http_exception_keeps_its_status_and_detail():
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Introuvable"}
