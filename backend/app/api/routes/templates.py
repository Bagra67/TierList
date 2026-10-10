import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_template_service
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.templates import (
    LastTierError,
    TemplateNotFoundError,
    TierNotFoundError,
    TileLimitReachedError,
    TileNotFoundError,
)
from app.models.template import Template
from app.models.user import User
from app.schemas.templates import (
    CreateTemplateRequest,
    CreateTileRequest,
    RenameTemplateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateSummaryResponse,
    UpdateTierRequest,
    UpdateTileRequest,
)
from app.services.templates import TemplateService, TemplateSummary, TierChanges, TileChanges

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

TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


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


@router.post("", status_code=201, responses=UNAUTHORIZED_RESPONSE)
def create_template(
    payload: CreateTemplateRequest, user: CurrentUserDep, service: TemplateServiceDep
) -> TemplateResponse:
    template: Template = service.create(user, payload.name)
    return TemplateResponse.model_validate(template)


@router.get("", responses=UNAUTHORIZED_RESPONSE)
def list_templates(user: CurrentUserDep, service: TemplateServiceDep) -> TemplateListResponse:
    summaries: list[TemplateSummary] = service.list_for_owner(user)

    items: list[TemplateSummaryResponse] = []
    for summary in summaries:
        items.append(TemplateSummaryResponse.model_validate(summary))
    return TemplateListResponse(items=items)


@router.get("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def get_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: TemplateServiceDep
) -> TemplateResponse:
    try:
        template: Template = service.get(user, template_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return TemplateResponse.model_validate(template)


@router.patch("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def rename_template(
    template_id: uuid.UUID,
    payload: RenameTemplateRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    try:
        template: Template = service.rename(user, template_id, payload.name)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=204, responses=TEMPLATE_NOT_FOUND_RESPONSES)
def delete_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: TemplateServiceDep
) -> None:
    try:
        service.delete(user, template_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc


@router.post("/{template_id}/tiers", status_code=201, responses=TEMPLATE_NOT_FOUND_RESPONSES)
def add_tier(
    template_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    try:
        template: Template = service.add_tier(user, template_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return TemplateResponse.model_validate(template)


@router.patch("/{template_id}/tiers/{tier_id}", responses=TIER_NOT_FOUND_RESPONSES)
def update_tier(
    template_id: uuid.UUID,
    tier_id: uuid.UUID,
    payload: UpdateTierRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    # Seuls les champs envoyés (non nuls) changent
    changes: TierChanges = TierChanges(**payload.model_dump(exclude_none=True))
    try:
        template: Template = service.update_tier(user, template_id, tier_id, changes)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TierNotFoundError as exc:
        raise _tier_not_found() from exc
    return TemplateResponse.model_validate(template)


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
) -> TemplateResponse:
    try:
        template: Template = service.delete_tier(user, template_id, tier_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TierNotFoundError as exc:
        raise _tier_not_found() from exc
    except LastTierError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.LAST_TIER,
            detail=messages.LAST_TIER,
        ) from exc
    return TemplateResponse.model_validate(template)


@router.post(
    "/{template_id}/tiles",
    status_code=201,
    responses={
        **TEMPLATE_NOT_FOUND_RESPONSES,
        409: {"model": ErrorResponse, "description": messages.TILE_LIMIT_REACHED_DESCRIPTION},
    },
)
def add_tile(
    template_id: uuid.UUID,
    payload: CreateTileRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    try:
        template: Template = service.add_tile(user, template_id, payload.text)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TileLimitReachedError as exc:
        # La limite part en param : le frontend l'affiche sans la recopier dans ses traductions
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TILE_LIMIT_REACHED,
            detail=messages.TILE_LIMIT_REACHED.format(max_tiles=exc.max_tiles),
            params={"max_tiles": exc.max_tiles},
        ) from exc
    return TemplateResponse.model_validate(template)


@router.patch("/{template_id}/tiles/{tile_id}", responses=TILE_NOT_FOUND_RESPONSES)
def update_tile(
    template_id: uuid.UUID,
    tile_id: uuid.UUID,
    payload: UpdateTileRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    # Seuls les champs envoyés (non nuls) changent
    changes: TileChanges = TileChanges(**payload.model_dump(exclude_none=True))
    try:
        template: Template = service.update_tile(user, template_id, tile_id, changes)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}/tiles/{tile_id}", responses=TILE_NOT_FOUND_RESPONSES)
def delete_tile(
    template_id: uuid.UUID,
    tile_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
) -> TemplateResponse:
    try:
        template: Template = service.delete_tile(user, template_id, tile_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    return TemplateResponse.model_validate(template)
