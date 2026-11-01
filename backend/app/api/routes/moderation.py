"""Espace de modération des super admins (docs/technical/moderation.md)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.api.dependencies import (
    ImageModerationServiceDep,
    ImageStorageDep,
    ModerationLogServiceDep,
    RecentUploadsServiceDep,
    SuperAdminDep,
    TemplateModerationServiceDep,
)
from app.api.presenters.images import recent_upload_response
from app.api.responses import SUPER_ADMIN_RESPONSES
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.moderation import (
    MODERATION_LOG_PAGE_SIZE_DEFAULT,
    MODERATION_LOG_PAGE_SIZE_MAX,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
    RECENT_UPLOADS_AUTHOR_FILTER_MAX_LENGTH,
    RECENT_UPLOADS_PAGE_SIZE_DEFAULT,
    RECENT_UPLOADS_PAGE_SIZE_MAX,
)
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.images import ImageModerationConflictError, ImageNotFoundError
from app.exceptions.templates import TemplateModerationConflictError, TemplateNotFoundError
from app.models.image import ImageStatus
from app.schemas.moderation import (
    ModerationActionResponse,
    ModerationLogResponse,
    ModerationReasonRequest,
    RecentUploadsResponse,
    SuperAdminResponse,
)
from app.services.moderation_log import ModerationLogPage
from app.services.recent_uploads import RecentUploadsPage

router = APIRouter(prefix="/moderation", tags=["moderation"])

IMAGE_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.IMAGE_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.IMAGE_MODERATION_CONFLICT_DESCRIPTION},
}

TEMPLATE_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.TEMPLATE_MODERATION_CONFLICT_DESCRIPTION},
}


def _template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


def _template_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_MODERATION_CONFLICT,
        detail=messages.TEMPLATE_MODERATION_CONFLICT,
    )


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


@router.get("/images", responses=SUPER_ADMIN_RESPONSES)
def list_recent_uploads(
    super_admin: SuperAdminDep,
    service: RecentUploadsServiceDep,
    storage: ImageStorageDep,
    limit: Annotated[
        int, Query(ge=1, le=RECENT_UPLOADS_PAGE_SIZE_MAX)
    ] = RECENT_UPLOADS_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
    # Texte cherché dans le nom ou l'e-mail de l'auteur, sans casse
    author: Annotated[str | None, Query(max_length=RECENT_UPLOADS_AUTHOR_FILTER_MAX_LENGTH)] = None,
    # Période d'envoi : à partir de created_after, avant created_before. Le fuseau horaire est
    # exigé : le frontend envoie les bornes des jours choisis dans le fuseau du super admin
    created_after: AwareDatetime | None = None,
    created_before: AwareDatetime | None = None,
    # Sans statut : les images visibles et masquées
    status: Literal["visible", "hidden"] | None = None,
) -> RecentUploadsResponse:
    # Les derniers envois (US-1.7), des plus récents aux plus anciens
    page: RecentUploadsPage = service.page(
        limit,
        offset,
        author,
        created_after,
        created_before,
        ImageStatus(status) if status is not None else None,
    )
    return RecentUploadsResponse(
        images=[recent_upload_response(storage, upload) for upload in page.uploads],
        has_more=page.has_more,
    )


@router.post(
    "/templates/{template_id}/hide", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def hide_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    # Masque un template (US-1.5) : plus de nouvelle salle ni de partie, le propriétaire voit le
    # motif
    try:
        service.hide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


@router.post(
    "/templates/{template_id}/unhide", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def unhide_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    # Réaffiche un template masqué : il retrouve l'état choisi par son propriétaire
    try:
        service.unhide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


# POST et non DELETE, comme pour les images : l'action porte un motif dans son corps
@router.post(
    "/templates/{template_id}/delete", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def delete_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    # Supprime un template comme son propriétaire le ferait (suppression logique, puis purge)
    try:
        service.delete(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc
