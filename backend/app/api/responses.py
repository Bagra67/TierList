from typing import Any

from app.constants import messages
from app.core.errors import ErrorResponse

UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": messages.UNAUTHORIZED_DESCRIPTION}
}

SUPER_ADMIN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    403: {"model": ErrorResponse, "description": messages.SUPER_ADMIN_REQUIRED_DESCRIPTION},
}
