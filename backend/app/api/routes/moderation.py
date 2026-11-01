"""Espace de modération des super admins (docs/technical/moderation.md)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import ModerationLogServiceDep, SuperAdminDep
from app.api.responses import SUPER_ADMIN_RESPONSES
from app.constants.moderation import (
    MODERATION_LOG_PAGE_SIZE_DEFAULT,
    MODERATION_LOG_PAGE_SIZE_MAX,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
)
from app.schemas.moderation import (
    ModerationActionResponse,
    ModerationLogResponse,
    SuperAdminResponse,
)
from app.services.moderation_log import ModerationLogPage

router = APIRouter(prefix="/moderation", tags=["moderation"])


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
