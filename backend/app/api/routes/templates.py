import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_template_service
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.templates import TemplateNotFoundError
from app.models.user import User
from app.schemas.templates import (
    CreateTemplateRequest,
    RenameTemplateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateSummaryResponse,
)
from app.services.templates import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATE_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
}

TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


@router.post("", status_code=201, responses=UNAUTHORIZED_RESPONSE)
def create_template(
    payload: CreateTemplateRequest, user: CurrentUserDep, service: TemplateServiceDep
) -> TemplateResponse:
    template = service.create(user, payload.name)
    return TemplateResponse.model_validate(template)


@router.get("", responses=UNAUTHORIZED_RESPONSE)
def list_templates(user: CurrentUserDep, service: TemplateServiceDep) -> TemplateListResponse:
    summaries = service.list_for_owner(user)

    items: list[TemplateSummaryResponse] = []
    for summary in summaries:
        items.append(TemplateSummaryResponse.model_validate(summary))
    return TemplateListResponse(items=items)


@router.get("/{template_id}", responses=TEMPLATE_NOT_FOUND_RESPONSES)
def get_template(
    template_id: uuid.UUID, user: CurrentUserDep, service: TemplateServiceDep
) -> TemplateResponse:
    try:
        template = service.get(user, template_id)
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
        template = service.rename(user, template_id, payload.name)
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
