from app.constants.i18n import Language

SITE_NAME = "TierList"
PAGE_TITLE_FORMAT = "{page} · " + SITE_NAME

PRIVACY_PAGE_PATH = "/privacy"
TERMS_PAGE_PATH = "/terms"
LEGAL_NOTICE_PAGE_PATH = "/legal"
PUBLIC_TEMPLATE_PAGE_PREFIX = "/marketplace/templates/"
DEFAULT_SHARE_IMAGE_PATH = "/og-image.png"

ROBOTS_PATH = "/robots.txt"
SITEMAP_PATH = "/sitemap.xml"
SITEMAP_MAX_URLS = 50_000
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_MEDIA_TYPE = "application/xml"

X_ROBOTS_TAG_HEADER = "X-Robots-Tag"
NOINDEX = "noindex"
ACCEPT_LANGUAGE_HEADER = "Accept-Language"
VARY_HEADER = "Vary"

OPEN_GRAPH_LOCALES: dict[Language, str] = {"fr": "fr_FR", "en": "en_US"}
