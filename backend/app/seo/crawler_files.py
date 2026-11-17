from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from app.constants.api import API_PREFIX
from app.constants.seo import SITEMAP_NAMESPACE


@dataclass(frozen=True)
class SitemapEntry:
    location: str
    last_modified: datetime | None = None


def robots_txt(sitemap_url: str | None) -> str:
    if sitemap_url is None:
        return "User-agent: *\nDisallow: /\n"
    return f"User-agent: *\nDisallow: {API_PREFIX}/\n\nSitemap: {sitemap_url}\n"


def sitemap_xml(entries: Sequence[SitemapEntry]) -> str:
    url_set: Element = Element("urlset", xmlns=SITEMAP_NAMESPACE)
    for entry in entries:
        url: Element = SubElement(url_set, "url")
        SubElement(url, "loc").text = entry.location
        if entry.last_modified is not None:
            SubElement(url, "lastmod").text = entry.last_modified.date().isoformat()
    return tostring(url_set, encoding="unicode", xml_declaration=True)
