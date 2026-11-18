import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import AfterValidator

from app.api.dependencies import CurrentUserDep, ImageStorageDep, MarketplaceServiceDep
from app.api.errors import invalid_cursor, template_not_found
from app.api.presenters.marketplace import (
    marketplace_template_response,
    public_template_response,
)
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.marketplace import (
    MARKETPLACE_PAGE_SIZE,
    SEARCH_QUERY_MAX_LENGTH,
    SEARCH_QUERY_MAX_WORDS,
    MarketplaceSort,
)
from app.constants.templates import CURSOR_MAX_LENGTH, TAG_MAX_LENGTH
from app.core.errors import ErrorResponse
from app.core.search_query import search_words
from app.exceptions.http import AppHTTPException
from app.exceptions.pagination import InvalidCursorError
from app.exceptions.templates import CannotLikeOwnTemplateError, TemplateNotFoundError
from app.schemas.marketplace import (
    LikeStateResponse,
    MarketplaceTagsResponse,
    MarketplaceTemplateListResponse,
    PublicTemplateResponse,
)
from app.services.marketplace import LikeState, MarketplacePage, PublicTemplate

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

TEMPLATE_NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION}
}
LIKE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    **TEMPLATE_NOT_FOUND_RESPONSE,
}


def _at_most_max_words(search: str | None) -> str | None:
    if search is not None:
        word_count: int = sum(len(words) for words in search_words(search))
        if word_count > SEARCH_QUERY_MAX_WORDS:
            raise ValueError(f"At most {SEARCH_QUERY_MAX_WORDS} words")
    return search


@router.get(
    "/templates",
    responses={400: {"model": ErrorResponse, "description": messages.INVALID_CURSOR_DESCRIPTION}},
)
def list_marketplace_templates(
    service: MarketplaceServiceDep,
    storage: ImageStorageDep,
    q: Annotated[
        str | None,
        Query(max_length=SEARCH_QUERY_MAX_LENGTH),
        AfterValidator(_at_most_max_words),
    ] = None,
    tag: Annotated[str | None, Query(max_length=TAG_MAX_LENGTH)] = None,
    sort: MarketplaceSort = MarketplaceSort.POPULAR,
    cursor: Annotated[str | None, Query(max_length=CURSOR_MAX_LENGTH)] = None,
    limit: Annotated[int, Query(ge=1, le=MARKETPLACE_PAGE_SIZE)] = MARKETPLACE_PAGE_SIZE,
) -> MarketplaceTemplateListResponse:
    """The public templates, without an account, by pages. `q` keeps the templates whose name or
    tags have words starting with every keyword (`|` separates alternatives), ignoring case and
    accents; `tag` keeps those with that tag. Sorted by number of likes (`popular`) or by date
    made public (`newest`). `cursor` is the `next_cursor` of the previous page, with the same
    `q`, `tag` and `sort`."""
    try:
        page: MarketplacePage = service.list_templates(q, tag, sort, cursor, limit)
    except InvalidCursorError as exc:
        raise invalid_cursor() from exc
    return MarketplaceTemplateListResponse(
        items=[marketplace_template_response(item, storage) for item in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/tags")
def list_marketplace_tags(service: MarketplaceServiceDep) -> MarketplaceTagsResponse:
    """The tags used by the most public templates, without an account, most used first."""
    return MarketplaceTagsResponse(tags=service.list_popular_tags())


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
        409: {"model": ErrorResponse, "description": messages.CANNOT_LIKE_OWN_TEMPLATE_DESCRIPTION},
    },
)
def like_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: MarketplaceServiceDep
) -> LikeStateResponse:
    """Likes a public template of another account. Liking it again changes nothing."""
    try:
        state: LikeState = service.like(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
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
