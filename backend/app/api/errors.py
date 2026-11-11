from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.exceptions.http import AppHTTPException


def template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
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
