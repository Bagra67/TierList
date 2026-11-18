from xml.etree.ElementTree import fromstring

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.constants.i18n import Language
from app.constants.seo import FRONTEND_PUBLIC_TEMPLATE_PREFIX, SITEMAP_NAMESPACE
from app.core.config import Settings, get_settings
from app.models.image import ImageStatus
from app.seo.head import PageHead
from app.services.marketplace import MarketplaceService
from app.services.seo import SeoService
from tests.integration.conftest import FAKE_IMAGE_BASE_URL, FakeImageStorage
from tests.integration.helpers import (
    add_tile_with_image,
    create_public_template,
    create_template,
    register,
    set_hidden,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"
ORIGIN = "https://tierlist.example.com"
SITEMAP_LOCATION = f"{{{SITEMAP_NAMESPACE}}}loc"
UNKNOWN_TEMPLATE_ID = "00000000-0000-4000-8000-000000000000"


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_public_template(auth_client, db_session, alice, ALICE_EMAIL)


def seo_service(db_session: Session, indexing_enabled: bool = True) -> SeoService:
    settings: Settings = get_settings().model_copy(
        update={"frontend_base_url": ORIGIN, "search_indexing_enabled": indexing_enabled}
    )
    return SeoService(settings, MarketplaceService(db_session), FakeImageStorage(stored={}))


def template_page(template_id: str) -> str:
    return f"{FRONTEND_PUBLIC_TEMPLATE_PREFIX}{template_id}"


def assert_unavailable(head: PageHead) -> None:
    assert head.status_code == 404
    assert not head.indexable


def sitemap_locations(service: SeoService) -> list[str | None]:
    sitemap_xml: str | None = service.sitemap_xml()
    assert sitemap_xml is not None
    return [location.text for location in fromstring(sitemap_xml).iter(SITEMAP_LOCATION)]


@pytest.mark.parametrize(
    ("path", "language", "title"),
    [
        ("/", "fr", "TierList · Classez ensemble, en direct"),
        ("/", "en", "TierList · Rank together, live"),
        ("/privacy", "fr", "Politique de confidentialité · TierList"),
        ("/terms", "en", "Terms of use · TierList"),
        ("/legal", "fr", "Mentions légales · TierList"),
        ("/marketplace", "fr", "Modèles publics · TierList"),
        ("/marketplace", "en", "Public templates · TierList"),
    ],
)
def test_a_fixed_public_page_is_indexable_with_its_title_and_canonical_url(
    db_session: Session, path: str, language: Language, title: str
):
    head: PageHead = seo_service(db_session).page_head(path, language)

    assert head.title == title
    assert head.canonical_url == f"{ORIGIN}{path}"
    assert head.image_url == f"{ORIGIN}/og-image.png"
    assert head.status_code == 200


@pytest.mark.parametrize("path", ["/r/K7P2QX", "/results/token", "/templates", "/login", "/nope"])
def test_any_other_page_is_not_indexable(db_session: Session, path: str):
    head: PageHead = seo_service(db_session).page_head(path, "fr")

    assert not head.indexable
    assert head.title == "TierList · Classez ensemble, en direct"
    assert head.status_code == 200


def test_no_page_is_indexable_when_indexing_is_disabled(db_session: Session, template_id: str):
    service: SeoService = seo_service(db_session, indexing_enabled=False)

    assert not service.page_head("/", "fr").indexable
    assert not service.page_head(template_page(template_id), "fr").indexable


def test_a_public_template_page_has_its_name_owner_and_canonical_url(
    db_session: Session, template_id: str
):
    head: PageHead = seo_service(db_session).page_head(template_page(template_id.upper()), "en")

    assert head.title == "Food · TierList"
    assert head.description == (
        "“Food” tier list template by alice. Rank its items together, live, on TierList."
    )
    assert head.canonical_url == f"{ORIGIN}/marketplace/templates/{template_id}"
    assert head.image_url == f"{ORIGIN}/og-image.png"


def test_a_public_template_page_shows_its_first_visible_image(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    _, hidden = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    _, visible = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    hidden.status = ImageStatus.HIDDEN
    db_session.flush()

    head: PageHead = seo_service(db_session).page_head(template_page(template_id), "fr")

    assert head.image_url == f"{FAKE_IMAGE_BASE_URL}/{visible.storage_key}"


@pytest.mark.parametrize("raw_template_id", ["not-a-uuid", UNKNOWN_TEMPLATE_ID])
def test_an_unknown_template_page_is_a_404_that_is_not_indexable(
    db_session: Session, raw_template_id: str
):
    assert_unavailable(seo_service(db_session).page_head(template_page(raw_template_id), "fr"))


def test_a_template_page_with_a_non_canonical_id_is_a_404_that_is_not_indexable(
    db_session: Session, template_id: str
):
    raw_template_id: str = template_id.replace("-", "")

    assert_unavailable(seo_service(db_session).page_head(template_page(raw_template_id), "fr"))


def test_a_private_template_page_is_a_404_that_is_not_indexable(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    private_template_id: str = create_template(auth_client, db_session, alice)

    assert_unavailable(seo_service(db_session).page_head(template_page(private_template_id), "fr"))


def test_a_hidden_template_page_is_a_404_that_is_not_indexable(
    db_session: Session, template_id: str
):
    set_hidden(db_session, template_id)

    assert_unavailable(seo_service(db_session).page_head(template_page(template_id), "fr"))


def test_robots_txt_points_to_the_sitemap_only_when_indexing_is_enabled(db_session: Session):
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in seo_service(db_session).robots_txt()
    assert seo_service(db_session, indexing_enabled=False).robots_txt() == (
        "User-agent: *\nDisallow: /\n"
    )


def test_the_sitemap_lists_the_fixed_pages_and_only_the_listed_templates(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
):
    private_template_id: str = create_template(auth_client, db_session, alice)
    hidden_template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    set_hidden(db_session, hidden_template_id)

    locations: list[str | None] = sitemap_locations(seo_service(db_session))

    assert locations == [
        f"{ORIGIN}/",
        f"{ORIGIN}/marketplace",
        f"{ORIGIN}/privacy",
        f"{ORIGIN}/terms",
        f"{ORIGIN}/legal",
        f"{ORIGIN}/marketplace/templates/{template_id}",
    ]
    assert not any(private_template_id in (location or "") for location in locations)


def test_there_is_no_sitemap_when_indexing_is_disabled(db_session: Session):
    assert seo_service(db_session, indexing_enabled=False).sitemap_xml() is None
