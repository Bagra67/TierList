from dataclasses import replace
from datetime import UTC, datetime
from xml.etree.ElementTree import Element, fromstring

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.api.dependencies import get_seo_service
from app.api.routes import seo
from app.constants.i18n import Language
from app.constants.seo import CRAWLER_FILES_CACHE_CONTROL, SITEMAP_NAMESPACE
from app.seo.crawler_files import SitemapEntry, robots_txt, sitemap_xml
from app.seo.head import PageHead, render_page
from app.seo.language import language_from_accept_language

INDEX_HTML = (
    '<!doctype html><html lang="fr"><head><title>TierList</title></head><body></body></html>'
)
SITEMAP_NAMESPACES: dict[str, str] = {"s": SITEMAP_NAMESPACE}
HEAD: PageHead = PageHead(
    language="fr",
    title="Snacks · TierList",
    description="Modèle de tier list « Snacks », par alice.",
    image_url="https://images.example.com/snack.webp",
    canonical_url="https://tierlist.example.com/marketplace/templates/1",
)


@pytest.mark.parametrize(
    ("header", "language"),
    [
        (None, "fr"),
        ("", "fr"),
        ("en-US,en;q=0.9", "en"),
        ("de-DE,de;q=0.9,en;q=0.5", "en"),
        ("en;q=0.4,fr-CH;q=0.8", "fr"),
        ("fr;q=0.5,en;q=0.5", "fr"),
        ("en;q=0,fr;q=0.1", "fr"),
        ("de,*;q=0.5", "fr"),
        ("en;q=oops", "fr"),
    ],
)
def test_the_page_language_is_the_preferred_supported_one_and_french_otherwise(
    header: str | None, language: Language
):
    assert language_from_accept_language(header) == language


def test_the_rendered_page_replaces_the_title_and_the_language():
    page: str = render_page(INDEX_HTML, replace(HEAD, language="en"))

    assert page.startswith('<!doctype html><html lang="en"><head>')
    assert page.count("<title>") == 1
    assert "<title>Snacks · TierList</title>" in page
    assert '<meta property="og:locale" content="en_US">' in page
    assert page.endswith("</head><body></body></html>")


def test_the_rendered_page_carries_the_open_graph_tags_and_the_canonical_url():
    page: str = render_page(INDEX_HTML, HEAD)

    assert '<meta property="og:title" content="Snacks · TierList">' in page
    assert '<meta property="og:image" content="https://images.example.com/snack.webp">' in page
    assert '<meta name="twitter:card" content="summary_large_image">' in page
    assert f'<link rel="canonical" href="{HEAD.canonical_url}">' in page
    assert f'<meta property="og:url" content="{HEAD.canonical_url}">' in page


def test_a_page_that_is_not_indexable_has_no_canonical_url():
    page: str = render_page(INDEX_HTML, replace(HEAD, canonical_url=None))

    assert "canonical" not in page
    assert "og:url" not in page


def test_user_values_cannot_inject_html_into_the_page():
    injected_name = '</title><script>alert("x")</script>'
    head: PageHead = replace(
        HEAD, title=injected_name, description=f'"><script>{injected_name}', image_url='x" a="b'
    )

    page: str = render_page(INDEX_HTML, head)

    assert "<script>" not in page
    assert page.count("</title>") == 1
    assert 'content="x&quot; a=&quot;b"' in page


def test_robots_txt_forbids_everything_without_a_sitemap():
    assert robots_txt(None) == "User-agent: *\nDisallow: /\n"


def test_robots_txt_lets_crawlers_read_everything_the_pages_render_from():
    assert robots_txt("https://tierlist.example.com/sitemap.xml") == (
        "User-agent: *\nAllow: /\n\nSitemap: https://tierlist.example.com/sitemap.xml\n"
    )


def test_the_sitemap_lists_every_url_with_its_escaped_location_and_last_change_day():
    xml: str = sitemap_xml(
        [
            SitemapEntry("https://tierlist.example.com/"),
            SitemapEntry(
                "https://tierlist.example.com/a?b=1&c=2", datetime(2026, 11, 3, 22, 5, tzinfo=UTC)
            ),
        ]
    )

    assert xml.startswith("<?xml")
    assert "&amp;" in xml
    url_set: Element = fromstring(xml)
    urls: list[tuple[str | None, str | None]] = [
        (
            url.findtext("s:loc", None, SITEMAP_NAMESPACES),
            url.findtext("s:lastmod", None, SITEMAP_NAMESPACES),
        )
        for url in url_set.findall("s:url", SITEMAP_NAMESPACES)
    ]
    assert urls == [
        ("https://tierlist.example.com/", None),
        ("https://tierlist.example.com/a?b=1&c=2", "2026-11-03"),
    ]


class FakeSeoService:
    def __init__(self, indexing_enabled: bool) -> None:
        self.indexing_enabled = indexing_enabled

    def robots_txt(self) -> str:
        return "User-agent: *\n"

    def sitemap_xml(self) -> str | None:
        return "<urlset/>" if self.indexing_enabled else None


def crawler_client(indexing_enabled: bool) -> TestClient:
    crawler_app: FastAPI = FastAPI()
    crawler_app.include_router(seo.router)
    crawler_app.dependency_overrides[get_seo_service] = lambda: FakeSeoService(indexing_enabled)
    return TestClient(crawler_app)


def test_robots_txt_is_served_as_plain_text_at_the_root():
    response: Response = crawler_client(indexing_enabled=False).get("/robots.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "User-agent: *\n"


def test_the_sitemap_is_served_as_xml_when_indexing_is_enabled():
    response: Response = crawler_client(indexing_enabled=True).get("/sitemap.xml")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert response.text == "<urlset/>"


def test_there_is_no_sitemap_when_indexing_is_disabled():
    assert crawler_client(indexing_enabled=False).get("/sitemap.xml").status_code == 404


@pytest.mark.parametrize(
    ("path", "indexing_enabled"),
    [("/robots.txt", False), ("/sitemap.xml", True), ("/sitemap.xml", False)],
)
def test_crawler_files_are_cached_for_a_few_minutes_only(path: str, indexing_enabled: bool):
    response: Response = crawler_client(indexing_enabled).get(path)

    assert response.headers["cache-control"] == CRAWLER_FILES_CACHE_CONTROL
