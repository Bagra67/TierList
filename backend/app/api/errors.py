from fastapi import Request, Response

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import handle_http_exception
from app.exceptions.http import AppHTTPException
from app.exceptions.templates import OfficialTemplateLockedError


def template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


def email_not_verified() -> AppHTTPException:
    return AppHTTPException(
        status_code=403,
        code=ErrorCode.EMAIL_NOT_VERIFIED,
        detail=messages.EMAIL_NOT_VERIFIED,
    )


def template_has_no_tiles() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_HAS_NO_TILES,
        detail=messages.TEMPLATE_HAS_NO_TILES,
    )


def template_hidden() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_HIDDEN,
        detail=messages.TEMPLATE_HIDDEN,
    )


def image_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.IMAGE_NOT_FOUND,
        detail=messages.IMAGE_NOT_FOUND,
    )


def invalid_cursor() -> AppHTTPException:
    return AppHTTPException(
        status_code=400,
        code=ErrorCode.INVALID_CURSOR,
        detail=messages.INVALID_CURSOR,
    )


def template_not_published() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_NOT_PUBLISHED,
        detail=messages.TEMPLATE_NOT_PUBLISHED,
    )


def official_template_locked(editor_name: str | None) -> AppHTTPException:
    if editor_name is None:
        return AppHTTPException(
            status_code=409,
            code=ErrorCode.OFFICIAL_TEMPLATE_LOCKED,
            detail=messages.OFFICIAL_TEMPLATE_LEASE_REQUIRED,
        )
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.OFFICIAL_TEMPLATE_LOCKED,
        detail=messages.OFFICIAL_TEMPLATE_LOCKED,
        params={"editor": editor_name},
    )


async def handle_official_template_locked(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, OfficialTemplateLockedError)
    return await handle_http_exception(request, official_template_locked(exc.editor_name))
