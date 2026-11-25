import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import TemplateVisibility
from app.models.template import Template
from app.models.user import User
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)

COPIES_MADE = 2


def copy_public_templates(
    session: Session, settings: Settings, sources: list[Template], players: list[User]
) -> int:
    source: Template | None = next(
        (template for template in sources if template.fits_player_limits), None
    )
    if source is None:
        return 0
    owner: User = next(player for player in players if player.id == source.owner_id)
    first_copier, second_copier = [player for player in players if player.id != owner.id][:2]
    templates: TemplateService = TemplateService(session, settings)
    templates.set_forks_allowed(owner, source.id, allowed=True)
    first_copy: Template = templates.copy(first_copier, source.id)
    templates.set_visibility(first_copier, first_copy.id, TemplateVisibility.PUBLIC)
    templates.set_forks_allowed(first_copier, first_copy.id, allowed=True)
    templates.copy(second_copier, first_copy.id)
    templates.set_visibility(first_copier, first_copy.id, TemplateVisibility.PRIVATE)
    logger.info(
        "Copies : « %s » copié deux fois de suite, la première copie rendue privée", source.name
    )
    return COPIES_MADE
