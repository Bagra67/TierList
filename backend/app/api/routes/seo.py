from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from app.api.dependencies import SeoServiceDep
from app.constants.seo import (
    CRAWLER_FILES_CACHE_CONTROL,
    ROBOTS_PATH,
    SITEMAP_MEDIA_TYPE,
    SITEMAP_PATH,
)

router = APIRouter(include_in_schema=False)

CRAWLER_FILES_HEADERS: dict[str, str] = {"Cache-Control": CRAWLER_FILES_CACHE_CONTROL}


@router.get(ROBOTS_PATH)
def robots(service: SeoServiceDep) -> PlainTextResponse:
    return PlainTextResponse(service.robots_txt(), headers=CRAWLER_FILES_HEADERS)


@router.get(SITEMAP_PATH)
def sitemap(service: SeoServiceDep) -> Response:
    sitemap_xml: str | None = service.sitemap_xml()
    if sitemap_xml is None:
        raise HTTPException(status_code=404, headers=CRAWLER_FILES_HEADERS)
    return Response(sitemap_xml, media_type=SITEMAP_MEDIA_TYPE, headers=CRAWLER_FILES_HEADERS)
