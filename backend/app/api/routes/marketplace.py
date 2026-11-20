import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import AfterValidator

from app.api.dependencies import CurrentUserDep, ImageStorageDep, MarketplaceServiceDep
from app.api.errors import email_not_verified, invalid_cursor, template_not_found
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
from app.exceptions.auth import EmailNotVerifiedError
from app.exceptions.http import AppHTTPException
from app.exceptions.pagination import InvalidCursorError
from app.exceptions.templates import CannotLikeOwnTemplateError, TemplateNotFoundError
from app.schemas.marketplace import (
    FeaturedTemplatesResponse,
    LikeStateResponse,
    LikeStatesResponse,
    MarketplaceTagsResponse,
    MarketplaceTemplateListResponse,
    PublicTemplateResponse,
    TemplateLikeStateResponse,
)
from app.services.marketplace import (
    LikeState,
    MarketplacePage,
    PublicTemplate,
    TemplateLikeState,
)

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


@router.get("/featured")
def list_featured_templates(
    service: MarketplaceServiceDep, storage: ImageStorageDep
) -> FeaturedTemplatesResponse:
    """The TierList picks, without an account: the featured official templates that are listed,
    most recently featured first, at most six."""
    return FeaturedTemplatesResponse(
        items=[marketplace_template_response(item, storage) for item in service.list_featured()]
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


@router.get("/likes", responses=UNAUTHORIZED_RESPONSE)
def list_like_states(
    template_ids: Annotated[
        list[uuid.UUID],
        Query(alias="template_id", min_length=1, max_length=MARKETPLACE_PAGE_SIZE),
    ],
    user: CurrentUserDep,
    service: MarketplaceServiceDep,
) -> LikeStatesResponse:
    """The account's like state of several public templates at once (one page of cards). The
    templates that are not listed are left out."""
    states: list[TemplateLikeState] = service.like_states(user, template_ids)
    return LikeStatesResponse(
        items=[TemplateLikeStateResponse.model_validate(state) for state in states]
    )


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
