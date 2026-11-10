import json
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.core.frontend import mount_frontend_after_api
from app.schemas.client_config import ClientConfigResponse

PAGE_START = "<!doctype html><head><title>TierList</title>"
PAGE_END = "</head><body></body>"
INDEX_HTML = PAGE_START + PAGE_END
CLIENT_CONFIG: ClientConfigResponse = ClientConfigResponse(
    sentry_dsn="https://public-key@sentry.example.invalid/1",
    environment="production",
    release="v1.2.3</script>",
)
CONFIG_ELEMENT_START = '<script type="application/json" id="tierlist-client-config">'
CONFIG_ELEMENT_END = "</script>"


def client_config_of(page: str) -> str:
    assert page.startswith(PAGE_START + CONFIG_ELEMENT_START)
    assert page.endswith(CONFIG_ELEMENT_END + PAGE_END)
    return page.removeprefix(PAGE_START + CONFIG_ELEMENT_START).removesuffix(
        CONFIG_ELEMENT_END + PAGE_END
    )


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log('ok')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    frontend_app: FastAPI = FastAPI()
    mount_frontend_after_api(frontend_app, dist, CLIENT_CONFIG)
    return TestClient(frontend_app)


def test_a_build_without_index_is_not_served_and_does_not_stop_the_app(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    frontend_app: FastAPI = FastAPI()

    mount_frontend_after_api(frontend_app, dist, CLIENT_CONFIG)

    assert TestClient(frontend_app).get("/templates").status_code == 404
    assert "Frontend non servi" in caplog.text


def test_a_page_without_head_end_is_served_as_it_is(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<p>TierList</p>", encoding="utf-8")
    frontend_app: FastAPI = FastAPI()
    mount_frontend_after_api(frontend_app, dist, CLIENT_CONFIG)

    assert TestClient(frontend_app).get("/templates").text == "<p>TierList</p>"
    assert "Config client non écrite" in caplog.text


def test_hashed_assets_are_cached_for_a_long_time(client: TestClient):
    response = client.get("/assets/index-abc123.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_a_missing_asset_is_a_404_not_the_page(client: TestClient):
    assert client.get("/assets/index-old.js").status_code == 404


@pytest.mark.parametrize("path", ["/", "/r/K7P2QX", "/templates/123", "/results/token"])
def test_frontend_routes_get_the_page_without_cache(client: TestClient, path: str):
    response = client.get(path)

    assert response.status_code == 200
    assert json.loads(client_config_of(response.text)) == CLIENT_CONFIG.model_dump()
    assert response.headers["cache-control"] == "no-cache"


def test_the_index_file_itself_carries_the_client_config(client: TestClient):
    response: Response = client.get("/index.html")

    assert response.status_code == 200
    assert json.loads(client_config_of(response.text)) == CLIENT_CONFIG.model_dump()


def test_the_client_config_cannot_close_its_script_element(client: TestClient):
    config_json: str = client_config_of(client.get("/").text)

    assert "<" not in config_json
    assert json.loads(config_json)["release"] == "v1.2.3</script>"


def test_head_requests_get_the_page_headers(client: TestClient):
    response = client.head("/r/K7P2QX")

    assert response.status_code == 200
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


def test_a_link_out_of_the_build_is_never_served(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    outside_file: Path = tmp_path / "secret.txt"
    (tmp_path / "frontend_dist" / "link.txt").write_text("secret", encoding="utf-8")
    real_resolve: Callable[[Path, bool], Path] = Path.resolve

    def resolve_the_link_like_the_file_system(path: Path, strict: bool = False) -> Path:
        return outside_file if path.name == "link.txt" else real_resolve(path, strict)

    monkeypatch.setattr(Path, "resolve", resolve_the_link_like_the_file_system)

    response: Response = client.get("/link.txt")

    assert "secret" not in response.text


def test_the_bare_api_prefix_is_not_a_page(client: TestClient):
    response = client.get("/api")

    assert response.status_code == 404
