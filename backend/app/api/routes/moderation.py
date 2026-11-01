"""Espace de modération des super admins (docs/technical/moderation.md)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.dependencies import (
    ImageModerationServiceDep,
    ModerationLogServiceDep,
    SuperAdminDep,
)
from app.api.responses import SUPER_ADMIN_RESPONSES
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.moderation import (
    MODERATION_LOG_PAGE_SIZE_DEFAULT,
    MODERATION_LOG_PAGE_SIZE_MAX,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
)
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.images import ImageModerationConflictError, ImageNotFoundError
from app.schemas.moderation import (
    ModerationActionResponse,
    ModerationLogResponse,
    ModerationReasonRequest,
    SuperAdminResponse,
)
from app.services.moderation_log import ModerationLogPage

router = APIRouter(prefix="/moderation", tags=["moderation"])

IMAGE_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.IMAGE_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.IMAGE_MODERATION_CONFLICT_DESCRIPTION},
}


def _image_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.IMAGE_NOT_FOUND,
        detail=messages.IMAGE_NOT_FOUND,
    )


def _image_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.IMAGE_MODERATION_CONFLICT,
        detail=messages.IMAGE_MODERATION_CONFLICT,
    )


@router.get("/log", responses=SUPER_ADMIN_RESPONSES)
def get_moderation_log(
    super_admin: SuperAdminDep,
    service: ModerationLogServiceDep,
    limit: Annotated[
        int, Query(ge=1, le=MODERATION_LOG_PAGE_SIZE_MAX)
    ] = MODERATION_LOG_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
    # Un super admin : ses actions seulement
    actor_id: uuid.UUID | None = None,
    # Texte cherché dans le libellé de la cible, sans casse
    target: Annotated[str | None, Query(max_length=MODERATION_TARGET_LABEL_MAX_LENGTH)] = None,
) -> ModerationLogResponse:
    # Le journal de modération (US-1.9), de l'action la plus récente à la plus ancienne
    page: ModerationLogPage = service.page(limit, offset, actor_id, target)
    return ModerationLogResponse(
        entries=[ModerationActionResponse.model_validate(entry) for entry in page.entries],
        has_more=page.has_more,
    )


@router.get("/super-admins", responses=SUPER_ADMIN_RESPONSES)
def list_super_admins(
    super_admin: SuperAdminDep, service: ModerationLogServiceDep
) -> list[SuperAdminResponse]:
    # Les auteurs possibles d'une action, pour le filtre du journal
    return [SuperAdminResponse.model_validate(user) for user in service.super_admins()]


# def et non async def : les appels au stockage S3 sont bloquants, FastAPI exécute donc ces routes
# dans son pool de threads
@router.post("/images/{image_id}/hide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def hide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    # Masque une image visible (US-1.4) : son adresse publique ne répond plus
    try:
        service.hide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.post("/images/{image_id}/unhide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def unhide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    # Réaffiche une image masquée, partout où elle était utilisée
    try:
        service.unhide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


# POST et non DELETE : l'action porte un motif dans son corps, et la ligne de l'image reste
@router.post("/images/{image_id}/delete", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def delete_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    # Supprime une image visible ou masquée, définitivement ; son empreinte est bannie (US-1.6)
    try:
        service.delete(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc
