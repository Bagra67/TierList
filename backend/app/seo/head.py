import re
from dataclasses import dataclass
from html import escape

from app.constants.api import FRONTEND_HEAD_END
from app.constants.i18n import Language
from app.constants.seo import OPEN_GRAPH_LOCALES, SITE_NAME

TITLE_ELEMENT = re.compile(r"<title>[^<]*</title>")
HTML_LANG_ATTRIBUTE = re.compile(r'(<html\b[^>]*\blang=")[^"]*(")')


@dataclass(frozen=True)
class PageHead:
    language: Language
    title: str
    description: str
    image_url: str
    canonical_url: str | None
    status_code: int = 200

    @property
    def indexable(self) -> bool:
        return self.canonical_url is not None


def render_page(index_html: str, head: PageHead) -> str:
    page: str = TITLE_ELEMENT.sub("", index_html, count=1)
    page = HTML_LANG_ATTRIBUTE.sub(rf"\g<1>{head.language}\g<2>", page, count=1)
    return page.replace(FRONTEND_HEAD_END, _head_elements(head) + FRONTEND_HEAD_END, 1)


def _head_elements(head: PageHead) -> str:
    elements: list[str] = [
        f"<title>{escape(head.title)}</title>",
        _meta("name", "description", head.description),
        _meta("property", "og:type", "website"),
        _meta("property", "og:site_name", SITE_NAME),
        _meta("property", "og:locale", OPEN_GRAPH_LOCALES[head.language]),
        _meta("property", "og:title", head.title),
        _meta("property", "og:description", head.description),
        _meta("property", "og:image", head.image_url),
        _meta("name", "twitter:card", "summary_large_image"),
    ]
    if head.canonical_url is not None:
        elements.append(f'<link rel="canonical" href="{escape(head.canonical_url)}">')
        elements.append(_meta("property", "og:url", head.canonical_url))
    return "".join(elements)


def _meta(attribute: str, key: str, content: str) -> str:
    return f'<meta {attribute}="{key}" content="{escape(content)}">'
