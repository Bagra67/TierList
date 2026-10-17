from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.frontend import mount_frontend

INDEX_HTML = "<!doctype html><title>TierList</title>"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Application neuve qui sert un faux build : index.html, un fichier hashé dans assets/, un
    favicon, et un fichier hors du build qui ne doit jamais être servi."""
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log('ok')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    frontend_app: FastAPI = FastAPI()
    mount_frontend(frontend_app, dist)
    return TestClient(frontend_app)


def test_hashed_assets_are_cached_for_a_long_time(client: TestClient):
    response = client.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_a_missing_asset_is_a_404_not_the_page(client: TestClient):
    # Un ancien fichier hashé, après un déploiement : pas de index.html servi comme du JavaScript
    assert client.get("/assets/index-old.js").status_code == 404


@pytest.mark.parametrize("path", ["/", "/r/K7P2QX", "/templates/123", "/results/token"])
def test_frontend_routes_get_the_page_without_cache(client: TestClient, path: str):
    response = client.get(path)

    assert response.status_code == 200
    assert response.text == INDEX_HTML
    assert response.headers["cache-control"] == "no-cache"


def test_root_files_of_the_build_are_served(client: TestClient):
    response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.text == "<svg/>"
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt"])
def test_files_outside_the_build_are_never_served(client: TestClient, path: str):
    response = client.get(path)

    assert "secret" not in response.text


def test_the_bare_api_prefix_is_not_a_page(client: TestClient):
    response = client.get("/api")

    assert response.status_code == 404
