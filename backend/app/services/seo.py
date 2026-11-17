import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.constants.auth import FRONTEND_HOME
from app.constants.i18n import Language
from app.constants.seo import (
    DEFAULT_SHARE_IMAGE_PATH,
    LEGAL_NOTICE_PAGE_PATH,
    PAGE_TITLE_FORMAT,
    PRIVACY_PAGE_PATH,
    PUBLIC_TEMPLATE_PAGE_PREFIX,
    SITEMAP_MAX_URLS,
    SITEMAP_PATH,
    TERMS_PAGE_PATH,
)
from app.core.config import Settings
from app.exceptions.seo import SearchIndexingDisabledError
from app.exceptions.templates import TemplateNotFoundError
from app.models.image import ImageStatus
from app.models.template import Template
from app.repositories import templates as template_repository
from app.seo.crawler_files import SitemapEntry, robots_txt, sitemap_xml
from app.seo.head import PageHead
from app.seo.texts import PAGE_TEXTS, PageTexts
from app.services.image_storage import ImageStorage
from app.services.marketplace import MarketplaceService, PublicTemplate

INDEXABLE_STATIC_PATHS: tuple[str, ...] = (
    FRONTEND_HOME,
    PRIVACY_PAGE_PATH,
    TERMS_PAGE_PATH,
    LEGAL_NOTICE_PAGE_PATH,
)


class SeoService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        marketplace: MarketplaceService,
        storage: ImageStorage,
    ) -> None:
        self._session = session
        self._settings = settings
        self._marketplace = marketplace
        self._storage = storage

    def page_head(self, path: str, language: Language) -> PageHead:
        texts: PageTexts = PAGE_TEXTS[language]
        static_title: str | None = _static_page_titles(texts).get(path)
        if static_title is not None:
            return self._head(language, static_title, texts.site_description, path)
        if path.startswith(PUBLIC_TEMPLATE_PAGE_PREFIX):
            return self._public_template_head(
                path.removeprefix(PUBLIC_TEMPLATE_PAGE_PREFIX), texts, language
            )
        return self._head(language, texts.site_title, texts.site_description, None)

    def robots_txt(self) -> str:
        sitemap_url: str | None = (
            self._url(SITEMAP_PATH) if self._settings.search_indexing_enabled else None
        )
        return robots_txt(sitemap_url)

    def sitemap_xml(self) -> str:
        if not self._settings.search_indexing_enabled:
            raise SearchIndexingDisabledError
        static_entries: list[SitemapEntry] = [
            SitemapEntry(self._url(path)) for path in INDEXABLE_STATIC_PATHS
        ]
        template_entries: list[SitemapEntry] = [
            SitemapEntry(self._url(_public_template_path(template_id)), updated_at)
            for template_id, updated_at in template_repository.list_listed_template_updates(
                self._session, datetime.now(UTC), SITEMAP_MAX_URLS - len(static_entries)
            )
        ]
        return sitemap_xml(static_entries + template_entries)

    def _public_template_head(
        self, raw_template_id: str, texts: PageTexts, language: Language
    ) -> PageHead:
        not_found: PageHead = self._head(
            language, texts.site_title, texts.site_description, None, status_code=404
        )
        try:
            template_id: uuid.UUID = uuid.UUID(raw_template_id)
        except ValueError:
            return not_found
        try:
            public_template: PublicTemplate = self._marketplace.get_template(template_id)
        except TemplateNotFoundError:
            return not_found
        template: Template = public_template.template
        return self._head(
            language,
            PAGE_TITLE_FORMAT.format(page=template.name),
            texts.template_description.format(name=template.name, owner=public_template.owner_name),
            _public_template_path(template_id),
            image_url=self._first_image_url(template),
        )

    def _head(
        self,
        language: Language,
        title: str,
        description: str,
        indexable_path: str | None,
        image_url: str | None = None,
        status_code: int = 200,
    ) -> PageHead:
        canonical_url: str | None = (
            self._url(indexable_path)
            if indexable_path is not None and self._settings.search_indexing_enabled
            else None
        )
        return PageHead(
            language=language,
            title=title,
            description=description,
            image_url=image_url or self._url(DEFAULT_SHARE_IMAGE_PATH),
            canonical_url=canonical_url,
            status_code=status_code,
        )

    def _first_image_url(self, template: Template) -> str | None:
        for tile in template.tiles:
            if tile.image is not None and tile.image.status == ImageStatus.VISIBLE:
                return self._storage.url(tile.image.storage_key)
        return None

    def _url(self, path: str) -> str:
        return self._settings.app_origin + path


def _static_page_titles(texts: PageTexts) -> dict[str, str]:
    return {
        FRONTEND_HOME: texts.site_title,
        PRIVACY_PAGE_PATH: PAGE_TITLE_FORMAT.format(page=texts.privacy_title),
        TERMS_PAGE_PATH: PAGE_TITLE_FORMAT.format(page=texts.terms_title),
        LEGAL_NOTICE_PAGE_PATH: PAGE_TITLE_FORMAT.format(page=texts.legal_notice_title),
    }


def _public_template_path(template_id: uuid.UUID) -> str:
    return f"{PUBLIC_TEMPLATE_PAGE_PREFIX}{template_id}"
