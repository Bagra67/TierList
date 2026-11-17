import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.core.frontend import mount_frontend_after_api
from app.schemas.client_config import ClientConfigResponse
from app.seo.head import PageHead

PAGE_START = '<!doctype html><html lang="fr"><head>'
PAGE_END = "</head><body></body></html>"
INDEX_HTML = PAGE_START + "<title>TierList</title>" + PAGE_END
INDEXABLE_HEAD: PageHead = PageHead(
    language="en",
    title="Privacy policy · TierList",
    description="What TierList does with your data.",
    image_url="https://tierlist.example.com/og-image.png",
    canonical_url="https://tierlist.example.com/privacy",
)
CLIENT_CONFIG: ClientConfigResponse = ClientConfigResponse(
    sentry_dsn="https://public-key@sentry.example.invalid/1",
    environment="production",
    release="v1.2.3</script>",
)
CONFIG_ELEMENT_START = '<script type="application/json" id="tierlist-client-config">'
CONFIG_ELEMENT_END = "</script>"


def client_config_of(page: str) -> str:
    _, _, after_start = page.partition(CONFIG_ELEMENT_START)
    config_json, separator, _ = after_start.partition(CONFIG_ELEMENT_END)
    assert separator
    return config_json


def frontend_client(dist: Path, head: PageHead = INDEXABLE_HEAD) -> TestClient:
    frontend_app: FastAPI = FastAPI()
    mount_frontend_after_api(frontend_app, dist, CLIENT_CONFIG, lambda: head)
    return TestClient(frontend_app)


def dist_with_index(tmp_path: Path) -> Path:
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    return dist


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist: Path = dist_with_index(tmp_path)
    (dist / "assets" / "index-abc123.js").write_text("console.log('ok')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    return frontend_client(dist)


def test_a_build_without_index_is_not_served_and_does_not_stop_the_app(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)

    client: TestClient = frontend_client(dist)

    assert client.get("/templates").status_code == 404
    assert "Frontend non servi" in caplog.text


def test_a_page_without_head_end_is_served_as_it_is(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    dist: Path = tmp_path / "frontend_dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<p>TierList</p>", encoding="utf-8")

    assert frontend_client(dist).get("/templates").text == "<p>TierList</p>"
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


def test_a_page_carries_the_title_language_and_tags_of_its_head(client: TestClient):
    page: str = client.get("/privacy").text

    assert page.startswith('<!doctype html><html lang="en"><head>')
    assert page.count("<title>") == 1
    assert "<title>Privacy policy · TierList</title>" in page
    assert '<meta name="description" content="What TierList does with your data.">' in page
    assert '<link rel="canonical" href="https://tierlist.example.com/privacy">' in page
    assert page.endswith(PAGE_END)


def test_an_indexable_page_has_no_noindex_header_and_varies_with_the_language(
    client: TestClient,
):
    response: Response = client.get("/privacy")

    assert "x-robots-tag" not in response.headers
    assert response.headers["vary"] == "Accept-Language"


def test_a_page_that_is_not_indexable_is_marked_noindex(tmp_path: Path):
    dist: Path = dist_with_index(tmp_path)
    head: PageHead = replace(INDEXABLE_HEAD, canonical_url=None)

    response: Response = frontend_client(dist, head).get("/r/K7P2QX")

    assert response.headers["x-robots-tag"] == "noindex"
    assert "canonical" not in response.text


def test_a_page_answers_with_the_status_of_its_head(tmp_path: Path):
    dist: Path = dist_with_index(tmp_path)
    head: PageHead = replace(INDEXABLE_HEAD, canonical_url=None, status_code=404)

    response: Response = frontend_client(dist, head).get("/marketplace/templates/unknown")

    assert response.status_code == 404
    assert response.headers["x-robots-tag"] == "noindex"
    assert json.loads(client_config_of(response.text)) == CLIENT_CONFIG.model_dump()
