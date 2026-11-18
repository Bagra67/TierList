import uuid

from app.constants.auth import FRONTEND_HOME
from app.constants.i18n import DEFAULT_PAGE_LANGUAGE, Language
from app.constants.seo import (
    DEFAULT_SHARE_IMAGE_PATH,
    FRONTEND_LEGAL_NOTICE,
    FRONTEND_PRIVACY,
    FRONTEND_PUBLIC_TEMPLATE_PREFIX,
    FRONTEND_TERMS,
    PAGE_TITLE_FORMAT,
    SITEMAP_MAX_URLS,
    SITEMAP_PATH,
)
from app.core.config import Settings
from app.exceptions.templates import TemplateNotFoundError
from app.models.image import ImageStatus
from app.models.template import Template
from app.seo.crawler_files import SitemapEntry, robots_txt, sitemap_xml
from app.seo.head import PageHead
from app.seo.texts import PAGE_TEXTS, PageTexts
from app.services.image_storage import ImageStorage
from app.services.marketplace import MarketplaceService, PublicTemplate

STATIC_PAGE_TITLES: dict[Language, dict[str, str]] = {
    language: {
        FRONTEND_HOME: texts.site_title,
        FRONTEND_PRIVACY: PAGE_TITLE_FORMAT.format(page=texts.privacy_title),
        FRONTEND_TERMS: PAGE_TITLE_FORMAT.format(page=texts.terms_title),
        FRONTEND_LEGAL_NOTICE: PAGE_TITLE_FORMAT.format(page=texts.legal_notice_title),
    }
    for language, texts in PAGE_TEXTS.items()
}


class SeoService:
    def __init__(
        self, settings: Settings, marketplace: MarketplaceService, storage: ImageStorage
    ) -> None:
        self._settings = settings
        self._marketplace = marketplace
        self._storage = storage

    def page_head(self, path: str, language: Language) -> PageHead:
        static_title: str | None = STATIC_PAGE_TITLES[language].get(path)
        if static_title is not None:
            return self._head(language, static_title, PAGE_TEXTS[language].site_description, path)
        if path.startswith(FRONTEND_PUBLIC_TEMPLATE_PREFIX):
            return self._public_template_head(
                path.removeprefix(FRONTEND_PUBLIC_TEMPLATE_PREFIX), language
            )
        return self._site_head(language)

    def robots_txt(self) -> str:
        sitemap_url: str | None = (
            self._url(SITEMAP_PATH) if self._settings.search_indexing_enabled else None
        )
        return robots_txt(sitemap_url)

    def sitemap_xml(self) -> str | None:
        if not self._settings.search_indexing_enabled:
            return None
        static_paths: list[str] = list(STATIC_PAGE_TITLES[DEFAULT_PAGE_LANGUAGE])
        static_entries: list[SitemapEntry] = [
            SitemapEntry(self._url(path)) for path in static_paths
        ]
        template_entries: list[SitemapEntry] = [
            SitemapEntry(self._url(_public_template_path(template_id)), updated_at)
            for template_id, updated_at in self._marketplace.list_template_updates(
                SITEMAP_MAX_URLS - len(static_paths)
            )
        ]
        return sitemap_xml(static_entries + template_entries)

    def _public_template_head(self, raw_template_id: str, language: Language) -> PageHead:
        try:
            template_id: uuid.UUID = _canonical_template_id(raw_template_id)
            public_template: PublicTemplate = self._marketplace.get_template(template_id)
        except ValueError, TemplateNotFoundError:
            return self._site_head(language, status_code=404)
        texts: PageTexts = PAGE_TEXTS[language]
        template: Template = public_template.template
        return self._head(
            language,
            PAGE_TITLE_FORMAT.format(page=template.name),
            texts.template_description.format(name=template.name, owner=public_template.owner_name),
            _public_template_path(template_id),
            image_url=self._first_image_url(template),
        )

    def _site_head(self, language: Language, status_code: int = 200) -> PageHead:
        texts: PageTexts = PAGE_TEXTS[language]
        return self._head(
            language, texts.site_title, texts.site_description, None, status_code=status_code
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


def _canonical_template_id(raw_template_id: str) -> uuid.UUID:
    template_id: uuid.UUID = uuid.UUID(raw_template_id)
    if str(template_id) != raw_template_id.lower():
        raise ValueError(raw_template_id)
    return template_id


def _public_template_path(template_id: uuid.UUID) -> str:
    return f"{FRONTEND_PUBLIC_TEMPLATE_PREFIX}{template_id}"
