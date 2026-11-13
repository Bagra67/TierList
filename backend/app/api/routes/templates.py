import uuid
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import (
    CurrentUserDep,
    ImageStorageDep,
    TemplateServiceDep,
)
from app.api.errors import (
    email_not_verified,
    image_not_found,
    template_has_no_tiles,
    template_hidden,
    template_not_found,
)
from app.api.presenters.templates import template_response
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.auth import EmailNotVerifiedError
from app.exceptions.http import AppHTTPException
from app.exceptions.images import ImageNotFoundError
from app.exceptions.templates import (
    LastTierError,
    TemplateHasNoTilesError,
    TemplateHiddenError,
    TemplateNotFoundError,
    TierNotFoundError,
    TileEmptyError,
    TileLimitReachedError,
    TileNotFoundError,
)
from app.models.template import Template
from app.schemas.templates import (
    CreateTemplateRequest,
    CreateTileRequest,
    RemovedTemplateListResponse,
    RemovedTemplateResponse,
    RenameTemplateRequest,
    SetTemplateVisibilityRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateSummaryResponse,
    UpdateTierRequest,
    UpdateTileRequest,
)
from app.services.templates import RemovedTemplate, TemplateSummary, TierChanges, TileChanges

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATE_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
}
TIER_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_OR_TIER_NOT_FOUND_DESCRIPTION},
}
TILE_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_OR_TILE_NOT_FOUND_DESCRIPTION},
}
SET_VISIBILITY_RESPONSES: dict[int | str, dict[str, Any]] = {
    **TEMPLATE_NOT_FOUND_RESPONSES,
    403: {"model": ErrorResponse, "description": messages.EMAIL_NOT_VERIFIED_DESCRIPTION},
    409: {
        "model": ErrorResponse,
        "description": messages.TEMPLATE_CANNOT_BE_MADE_PUBLIC_DESCRIPTION,
    },
}
TILE_EMPTY_RESPONSE: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": messages.TILE_EMPTY_DESCRIPTION},
}


def _tier_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TIER_NOT_FOUND,
        detail=messages.TIER_NOT_FOUND,
    )


def _tile_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TILE_NOT_FOUND,
        detail=messages.TILE_NOT_FOUND,
    )


def _tile_empty() -> AppHTTPException:
    return AppHTTPException(
        status_code=422,
        code=ErrorCode.TILE_EMPTY,
        detail=messages.TILE_EMPTY,
    )


@router.post("", status_code=201, responses=UNAUTHORIZED_RESPONSE)
def create_template(
    payload: CreateTemplateRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Creates a template with the six default tiers (S to E) and no tile."""
    template: Template = service.create(user, payload.name)
    return template_response(template, storage)


@router.get("", responses=UNAUTHORIZED_RESPONSE)
def list_templates(user: CurrentUserDep, service: TemplateServiceDep) -> TemplateListResponse:
    """The account's active templates, with their number of tiles, most recently modified first.
    Each template gives its moderation decision and the images removed from its tiles."""
    summaries: list[TemplateSummary] = service.list_for_owner(user)

    items: list[TemplateSummaryResponse] = []
    for summary in summaries:
        items.append(TemplateSummaryResponse.model_validate(summary))
    return TemplateListResponse(items=items)


@router.get("/removed", responses=UNAUTHORIZED_RESPONSE)
def list_removed_templates(
    user: CurrentUserDep, service: TemplateServiceDep
) -> RemovedTemplateListResponse:
    """The account's templates deleted by moderation and not purged yet, with the date and the
    reason."""
    removed_templates: list[RemovedTemplate] = service.list_removed_by_moderation(user)
    return RemovedTemplateListResponse(
        items=[RemovedTemplateResponse.model_validate(template) for template in removed_templates]
    )


@router.get("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def get_template(
    template_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """A template of the account, with its tiers and its tiles sorted by position. 404 for a deleted
    template or one of another account."""
    try:
        template: Template = service.get(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return template_response(template, storage)


@router.patch("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def rename_template(
    template_id: uuid.UUID,
    payload: RenameTemplateRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Renames a template; its last modification date is updated."""
    try:
        template: Template = service.rename(user, template_id, payload.name)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return template_response(template, storage)


@router.put("/{template_id}/visibility", responses=SET_VISIBILITY_RESPONSES)
def set_template_visibility(
    template_id: uuid.UUID,
    payload: SetTemplateVisibilityRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Makes a template public or private, by its owner. Making it public requires a confirmed email
    address, a template not hidden by moderation and at least one tile. The date of the first
    publication is kept when the template goes back to private."""
    try:
        template: Template = service.set_visibility(user, template_id, payload.visibility)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except EmailNotVerifiedError as exc:
        raise email_not_verified() from exc
    except TemplateHiddenError as exc:
        raise template_hidden() from exc
    except TemplateHasNoTilesError as exc:
        raise template_has_no_tiles() from exc
    return template_response(template, storage)


@router.delete("/{template_id}", status_code=204, responses=TEMPLATE_NOT_FOUND_RESPONSES)
def delete_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: TemplateServiceDep
) -> None:
    """Deletes a template: it disappears right away for its owner, and it is erased for good after
    the retention period. Games already played keep their frozen version."""
    try:
        service.delete(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc


@router.post("/{template_id}/tiers", status_code=201, responses=TEMPLATE_NOT_FOUND_RESPONSES)
def add_tier(
    template_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Adds a tier at the bottom of the template, named "?", color #9AA0B4."""
    try:
        template: Template = service.add_tier(user, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return template_response(template, storage)


@router.patch("/{template_id}/tiers/{tier_id}", responses=TIER_NOT_FOUND_RESPONSES)
def update_tier(
    template_id: uuid.UUID,
    tier_id: uuid.UUID,
    payload: UpdateTierRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Changes the name, the color and/or the position of a tier; the other tiers are shifted. A
    position past the end puts the tier last."""
    changes: TierChanges = TierChanges(**payload.model_dump(exclude_none=True))
    try:
        template: Template = service.update_tier(user, template_id, tier_id, changes)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TierNotFoundError as exc:
        raise _tier_not_found() from exc
    return template_response(template, storage)


@router.delete(
    "/{template_id}/tiers/{tier_id}",
    responses={
        **TIER_NOT_FOUND_RESPONSES,
        409: {"model": ErrorResponse, "description": messages.LAST_TIER_DESCRIPTION},
    },
)
def delete_tier(
    template_id: uuid.UUID,
    tier_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Deletes a tier; the following ones move up. Refused (409) for the template's last tier."""
    try:
        template: Template = service.delete_tier(user, template_id, tier_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TierNotFoundError as exc:
        raise _tier_not_found() from exc
    except LastTierError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.LAST_TIER,
            detail=messages.LAST_TIER,
        ) from exc
    return template_response(template, storage)


@router.post(
    "/{template_id}/tiles",
    status_code=201,
    responses={
        **TEMPLATE_NOT_FOUND_RESPONSES,
        404: {
            "model": ErrorResponse,
            "description": messages.TEMPLATE_OR_IMAGE_NOT_FOUND_DESCRIPTION,
        },
        409: {"model": ErrorResponse, "description": messages.TILE_LIMIT_REACHED_DESCRIPTION},
        **TILE_EMPTY_RESPONSE,
    },
)
def add_tile(
    template_id: uuid.UUID,
    payload: CreateTileRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Adds a tile at the end of the template: a text, an image already uploaded by the account
    (POST /images), or both. Refused (409) past the maximum number of tiles (`max_tiles`)."""
    try:
        template: Template = service.add_tile(user, template_id, payload.text, payload.image_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except ImageNotFoundError as exc:
        raise image_not_found() from exc
    except TileEmptyError as exc:
        raise _tile_empty() from exc
    except TileLimitReachedError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TILE_LIMIT_REACHED,
            detail=messages.TILE_LIMIT_REACHED.format(max_tiles=exc.max_tiles),
            params={"max_tiles": exc.max_tiles},
        ) from exc
    return template_response(template, storage)


@router.patch(
    "/{template_id}/tiles/{tile_id}",
    responses={
        **TILE_NOT_FOUND_RESPONSES,
        404: {
            "model": ErrorResponse,
            "description": messages.TEMPLATE_TILE_OR_IMAGE_NOT_FOUND_DESCRIPTION,
        },
        **TILE_EMPTY_RESPONSE,
    },
)
def update_tile(
    template_id: uuid.UUID,
    tile_id: uuid.UUID,
    payload: UpdateTileRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Changes the text, the image and/or the position of a tile. An explicit `null` removes the
    text or the image, as long as the tile keeps the other; `position: null` is ignored."""
    changes: TileChanges = TileChanges(**payload.model_dump(exclude_unset=True))
    if payload.position is None:
        changes.pop("position", None)
    try:
        template: Template = service.update_tile(user, template_id, tile_id, changes)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    except ImageNotFoundError as exc:
        raise image_not_found() from exc
    except TileEmptyError as exc:
        raise _tile_empty() from exc
    return template_response(template, storage)


@router.delete("/{template_id}/tiles/{tile_id}", responses=TILE_NOT_FOUND_RESPONSES)
def delete_tile(
    template_id: uuid.UUID,
    tile_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Deletes a tile; the following ones move up."""
    try:
        template: Template = service.delete_tile(user, template_id, tile_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    return template_response(template, storage)
