import uuid

from fastapi import APIRouter

from app.api.dependencies import ImageStorageDep, MarketplaceServiceDep
from app.api.errors import template_not_found
from app.api.presenters.marketplace import public_template_response
from app.constants import messages
from app.core.errors import ErrorResponse
from app.exceptions.templates import TemplateNotFoundError
from app.schemas.marketplace import PublicTemplateResponse
from app.services.marketplace import PublicTemplate

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get(
    "/templates/{template_id}",
    responses={
        404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION}
    },
)
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
