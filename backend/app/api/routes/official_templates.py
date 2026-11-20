import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

from app.api.dependencies import ImageStorageDep, OfficialTemplateServiceDep, SuperAdminDep
from app.api.errors import (
    template_has_no_tiles,
    template_hidden,
    template_not_found,
)
from app.api.presenters.templates import official_template_summary_response, template_response
from app.api.responses import SUPER_ADMIN_RESPONSES
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.templates import (
    TemplateHasNoTilesError,
    TemplateHiddenError,
    TemplateNotFoundError,
    TemplateNotPublishedError,
)
from app.models.template import Template
from app.models.user import User
from app.schemas.templates import (
    CreateTemplateRequest,
    OfficialTemplateListResponse,
    TemplateResponse,
)

router = APIRouter(prefix="/moderation/official-templates", tags=["moderation"])

NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
}
LOCK_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    **NOT_FOUND_RESPONSE,
    409: {"model": ErrorResponse, "description": messages.OFFICIAL_TEMPLATE_LOCKED_DESCRIPTION},
}
EDITORIAL_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    **NOT_FOUND_RESPONSE,
    409: {
        "model": ErrorResponse,
        "description": messages.OFFICIAL_TEMPLATE_CHANGE_CONFLICT_DESCRIPTION,
    },
}


def _template_not_published() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_NOT_PUBLISHED,
        detail=messages.TEMPLATE_NOT_PUBLISHED,
    )


@router.get("", responses=SUPER_ADMIN_RESPONSES)
def list_official_templates(
    super_admin: SuperAdminDep, service: OfficialTemplateServiceDep
) -> OfficialTemplateListResponse:
    """The official templates, drafts and published ones, most recently changed first, with the
    super admin holding the edit lease of each."""
    return OfficialTemplateListResponse(
        items=[official_template_summary_response(summary) for summary in service.list()]
    )


@router.post("", status_code=201, responses=SUPER_ADMIN_RESPONSES)
def create_official_template(
    payload: CreateTemplateRequest,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Creates an official template, owned by the site, as a draft with the default tiers. The
    super admin who creates it holds its edit lease. Written to the log."""
    template: Template = service.create(super_admin, payload.name)
    return template_response(template, storage)


@router.post("/{template_id}/lock", responses=LOCK_RESPONSES)
def lock_official_template(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Takes or renews the edit lease of an official template, for a few minutes: the editor
    renews it while the page is open. Refused (409, with the `editor` display name) while another
    super admin holds it. The template's content is changed through the /templates routes."""
    try:
        template: Template = service.lock(super_admin, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return template_response(template, storage)


@router.delete(
    "/{template_id}/lock",
    status_code=204,
    responses={**SUPER_ADMIN_RESPONSES, **NOT_FOUND_RESPONSE},
)
def unlock_official_template(
    template_id: uuid.UUID, super_admin: SuperAdminDep, service: OfficialTemplateServiceDep
) -> None:
    """Gives back the edit lease of an official template, when the editor leaves the page. Does
    nothing when another super admin holds it."""
    try:
        service.unlock(super_admin, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc


def _editorial_change(
    change: Callable[[User, uuid.UUID], Template],
    super_admin: User,
    template_id: uuid.UUID,
    storage: ImageStorageDep,
) -> TemplateResponse:
    try:
        template: Template = change(super_admin, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TemplateHasNoTilesError as exc:
        raise template_has_no_tiles() from exc
    except TemplateHiddenError as exc:
        raise template_hidden() from exc
    except TemplateNotPublishedError as exc:
        raise _template_not_published() from exc
    return template_response(template, storage)


@router.post("/{template_id}/publish", responses=EDITORIAL_RESPONSES)
def publish_official_template(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Publishes a draft official template: it is listed, playable and liked like any public
    template, signed by TierList. Refused without tiles or while hidden. Written to the log."""
    return _editorial_change(service.publish, super_admin, template_id, storage)


@router.post("/{template_id}/unpublish", responses=EDITORIAL_RESPONSES)
def unpublish_official_template(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Turns a published official template back into a draft, seen by the super admins only; it
    leaves the TierList picks. Games already started go on. Written to the log."""
    return _editorial_change(service.unpublish, super_admin, template_id, storage)


@router.post("/{template_id}/feature", responses=EDITORIAL_RESPONSES)
def feature_official_template(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Puts a published official template in the TierList picks, first on the home page and on
    the public templates. Refused for a draft. Written to the log."""
    return _editorial_change(service.feature, super_admin, template_id, storage)


@router.post("/{template_id}/unfeature", responses=EDITORIAL_RESPONSES)
def unfeature_official_template(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: OfficialTemplateServiceDep,
    storage: ImageStorageDep,
) -> TemplateResponse:
    """Takes an official template out of the TierList picks. Written to the log."""
    return _editorial_change(service.unfeature, super_admin, template_id, storage)


@router.delete("/{template_id}", status_code=204, responses=EDITORIAL_RESPONSES)
def delete_official_template(
    template_id: uuid.UUID, super_admin: SuperAdminDep, service: OfficialTemplateServiceDep
) -> None:
    """Deletes an official template like any template: the super admins can restore or erase it
    from the deleted templates until the purge. Written to the log."""
    try:
        service.delete(super_admin, template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
