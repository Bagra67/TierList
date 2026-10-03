from typing import Annotated

import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient

from app.constants.error_codes import ErrorCode
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.exceptions.http import AppHTTPException


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

    @app.get("/search")
    def search(query: Annotated[str, Query(min_length=3)]) -> dict[str, str]:
        return {"query": query}

    @app.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="Not here")

    @app.get("/protected")
    def protected() -> None:
        raise AppHTTPException(
            status_code=401,
            code=ErrorCode.NOT_AUTHENTICATED,
            detail="Authentication required",
            params={"retry_after": 30},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return app


client = TestClient(create_app(), raise_server_exceptions=False)


def test_unexpected_error_returns_generic_500(capsys: pytest.CaptureFixture[str]):
    configure_logging("INFO")

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error", "code": "internal_error"}
    assert "secret internal detail" not in response.text

    stderr = capsys.readouterr().err
    assert "ERROR:" in stderr
    assert "app.core.errors - Erreur non gérée sur GET /boom" in stderr
    assert "RuntimeError: secret internal detail" in stderr


def test_validation_error_lists_invalid_fields_with_their_code():
    response = client.get("/items/abc")

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Invalid request"
    assert body["code"] == "validation_error"
    codes = {error["field"]: error["code"] for error in body["errors"]}
    assert codes == {"path.item_id": "int_parsing", "query.limit": "missing"}
    assert all(error["message"] for error in body["errors"])


def test_validation_error_exposes_the_constraint_as_params():
    response = client.get("/search", params={"query": "ab"})

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["code"] == "string_too_short"
    assert error["params"] == {"min_length": 3}


def test_app_http_exception_returns_its_code_params_and_headers():
    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
        "code": "not_authenticated",
        "params": {"retry_after": 30},
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_plain_http_exception_keeps_its_status_and_detail_with_a_generic_code():
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not here", "code": "http_error"}


def test_unknown_route_uses_the_error_format():
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "http_error"}
