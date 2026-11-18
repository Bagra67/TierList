import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import CurrentUserDep, ImageStorageDep, MarketplaceServiceDep
from app.api.errors import email_not_verified, template_not_found
from app.api.presenters.marketplace import public_template_response
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.auth import EmailNotVerifiedError
from app.exceptions.http import AppHTTPException
from app.exceptions.templates import CannotLikeOwnTemplateError, TemplateNotFoundError
from app.schemas.marketplace import LikeStateResponse, PublicTemplateResponse
from app.services.marketplace import LikeState, PublicTemplate

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

TEMPLATE_NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION}
}
LIKE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    **TEMPLATE_NOT_FOUND_RESPONSE,
}


@router.get("/templates/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSE)
def get_public_template(
    template_id: uuid.UUID,
    service: MarketplaceServiceDep,
    storage: ImageStorageDep,
) -> PublicTemplateResponse:
    """A public template, without an account. 404 when the template is not public, is hidden by
    moderation, is deleted or its owner is banned, without saying which."""
    try:
        public_template: PublicTemplate = service.get_template(template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return public_template_response(public_template, storage)


@router.get("/templates/{template_id}/like", responses=LIKE_RESPONSES)
def get_like(
    template_id: uuid.UUID, user: CurrentUserDep, service: MarketplaceServiceDep
) -> LikeStateResponse:
    """Whether the account likes this public template, and its number of likes."""
    try:
        state: LikeState = service.like_state(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return LikeStateResponse(
        liked=state.liked, like_count=state.like_count, can_like=state.can_like
    )


@router.put(
    "/templates/{template_id}/like",
    responses={
        **LIKE_RESPONSES,
        403: {"model": ErrorResponse, "description": messages.EMAIL_NOT_VERIFIED_DESCRIPTION},
        409: {"model": ErrorResponse, "description": messages.CANNOT_LIKE_OWN_TEMPLATE_DESCRIPTION},
    },
)
def like_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: MarketplaceServiceDep
) -> LikeStateResponse:
    """Likes a public template of another account, with a confirmed email address. Liking it
    again changes nothing."""
    try:
        state: LikeState = service.like(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except EmailNotVerifiedError as exc:
        raise email_not_verified() from exc
    except CannotLikeOwnTemplateError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.CANNOT_LIKE_OWN_TEMPLATE,
            detail=messages.CANNOT_LIKE_OWN_TEMPLATE,
        ) from exc
    return LikeStateResponse(
        liked=state.liked, like_count=state.like_count, can_like=state.can_like
    )


@router.delete("/templates/{template_id}/like", responses=LIKE_RESPONSES)
def unlike_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: MarketplaceServiceDep
) -> LikeStateResponse:
    """Removes the account's like of a public template. Without a like, changes nothing."""
    try:
        state: LikeState = service.unlike(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return LikeStateResponse(
        liked=state.liked, like_count=state.like_count, can_like=state.can_like
    )
