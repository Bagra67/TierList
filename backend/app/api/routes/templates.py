import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_image_storage, get_template_service
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.images import ImageNotFoundError
from app.exceptions.templates import (
    LastTierError,
    TemplateNotFoundError,
    TierNotFoundError,
    TileEmptyError,
    TileLimitReachedError,
    TileNotFoundError,
)
from app.models.template import Template
from app.models.user import User
from app.schemas.templates import (
    IMAGE_URL_CONTEXT_KEY,
    CreateTemplateRequest,
    CreateTileRequest,
    RenameTemplateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateSummaryResponse,
    UpdateTierRequest,
    UpdateTileRequest,
)
from app.services.image_storage import ImageStorage
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
TILE_EMPTY_RESPONSE: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": messages.TILE_EMPTY_DESCRIPTION},
}

TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
# Donne l'adresse publique des images des tuiles
ImageStorageDep = Annotated[ImageStorage, Depends(get_image_storage)]


def _template_response(template: Template, storage: ImageStorage) -> TemplateResponse:
    return TemplateResponse.model_validate(template, context={IMAGE_URL_CONTEXT_KEY: storage.url})


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


def _image_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.IMAGE_NOT_FOUND,
        detail=messages.IMAGE_NOT_FOUND,
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
    template: Template = service.create(user, payload.name)
    return _template_response(template, storage)


@router.get("", responses=UNAUTHORIZED_RESPONSE)
def list_templates(user: CurrentUserDep, service: TemplateServiceDep) -> TemplateListResponse:
    summaries: list[TemplateSummary] = service.list_for_owner(user)

    items: list[TemplateSummaryResponse] = []
    for summary in summaries:
        items.append(TemplateSummaryResponse.model_validate(summary))
    return TemplateListResponse(items=items)


@router.get("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def get_template(
    template_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    try:
        template: Template = service.get(user, template_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return _template_response(template, storage)


@router.patch("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def rename_template(
    template_id: uuid.UUID,
    payload: RenameTemplateRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    try:
        template: Template = service.rename(user, template_id, payload.name)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return _template_response(template, storage)


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
    storage: ImageStorageDep,
) -> TemplateResponse:
    try:
        template: Template = service.add_tier(user, template_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    return _template_response(template, storage)


@router.patch("/{template_id}/tiers/{tier_id}", responses=TIER_NOT_FOUND_RESPONSES)
def update_tier(
    template_id: uuid.UUID,
    tier_id: uuid.UUID,
    payload: UpdateTierRequest,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    # Seuls les champs envoyés (non nuls) changent
    changes: TierChanges = TierChanges(**payload.model_dump(exclude_none=True))
    try:
        template: Template = service.update_tier(user, template_id, tier_id, changes)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TierNotFoundError as exc:
        raise _tier_not_found() from exc
    return _template_response(template, storage)


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
    return _template_response(template, storage)


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
    try:
        template: Template = service.add_tile(user, template_id, payload.text, payload.image_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except TileEmptyError as exc:
        raise _tile_empty() from exc
    except TileLimitReachedError as exc:
        # La limite part en param : le frontend l'affiche sans la recopier dans ses traductions
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TILE_LIMIT_REACHED,
            detail=messages.TILE_LIMIT_REACHED.format(max_tiles=exc.max_tiles),
            params={"max_tiles": exc.max_tiles},
        ) from exc
    return _template_response(template, storage)


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
    # Seuls les champs envoyés changent : null retire le texte ou l'image, mais une position
    # null est ignorée (une tuile a toujours une place)
    changes: TileChanges = TileChanges(**payload.model_dump(exclude_unset=True))
    if payload.position is None:
        changes.pop("position", None)
    try:
        template: Template = service.update_tile(user, template_id, tile_id, changes)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except TileEmptyError as exc:
        raise _tile_empty() from exc
    return _template_response(template, storage)


@router.delete("/{template_id}/tiles/{tile_id}", responses=TILE_NOT_FOUND_RESPONSES)
def delete_tile(
    template_id: uuid.UUID,
    tile_id: uuid.UUID,
    user: CurrentUserDep,
    service: TemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    try:
        template: Template = service.delete_tile(user, template_id, tile_id)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TileNotFoundError as exc:
        raise _tile_not_found() from exc
    return _template_response(template, storage)
