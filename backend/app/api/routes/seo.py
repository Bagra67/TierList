from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from app.api.dependencies import SeoServiceDep
from app.constants.seo import ROBOTS_PATH, SITEMAP_MEDIA_TYPE, SITEMAP_PATH

router = APIRouter(include_in_schema=False)


@router.get(ROBOTS_PATH)
def robots(service: SeoServiceDep) -> PlainTextResponse:
    return PlainTextResponse(service.robots_txt())


@router.get(SITEMAP_PATH)
def sitemap(service: SeoServiceDep) -> Response:
    sitemap_xml: str | None = service.sitemap_xml()
    if sitemap_xml is None:
        raise HTTPException(status_code=404)
    return Response(sitemap_xml, media_type=SITEMAP_MEDIA_TYPE)
