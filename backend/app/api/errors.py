from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.exceptions.http import AppHTTPException


def template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


def image_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.IMAGE_NOT_FOUND,
        detail=messages.IMAGE_NOT_FOUND,
    )
