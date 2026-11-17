from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from app.api.dependencies import SeoServiceDep
from app.constants.seo import ROBOTS_PATH, SITEMAP_MEDIA_TYPE, SITEMAP_PATH
from app.exceptions.seo import SearchIndexingDisabledError

router = APIRouter(include_in_schema=False)


@router.get(ROBOTS_PATH)
def robots(service: SeoServiceDep) -> PlainTextResponse:
    return PlainTextResponse(service.robots_txt())


@router.get(SITEMAP_PATH)
def sitemap(service: SeoServiceDep) -> Response:
    try:
        return Response(service.sitemap_xml(), media_type=SITEMAP_MEDIA_TYPE)
    except SearchIndexingDisabledError as exc:
        raise HTTPException(status_code=404) from exc
