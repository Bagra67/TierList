import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import TemplateVisibility
from app.models.template import Template
from app.models.user import User
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)


def copy_public_templates(
    session: Session,
    settings: Settings,
    sources: list[Template],
    players: list[User],
    chained_copies: int,
) -> int:
    source: Template | None = next(
        (template for template in sources if template.fits_player_limits), None
    )
    if source is None or chained_copies < 1:
        return 0
    owner: User | None = next((player for player in players if player.id == source.owner_id), None)
    copiers: list[User] = [player for player in players if player.id != source.owner_id][
        :chained_copies
    ]
    if owner is None or len(copiers) < chained_copies:
        return 0
    templates: TemplateService = TemplateService(session, settings)
    templates.set_forks_allowed(owner, source.id, allowed=True)
    parent_owner: User = owner
    parent: Template = source
    copies: list[Template] = []
    for copier in copiers:
        if copies:
            templates.set_visibility(parent_owner, parent.id, TemplateVisibility.PUBLIC)
            templates.set_forks_allowed(parent_owner, parent.id, allowed=True)
        parent = templates.copy(copier, parent.id)
        parent_owner = copier
        copies.append(parent)
    if len(copies) > 1:
        templates.set_visibility(copiers[0], copies[0].id, TemplateVisibility.PRIVATE)
    logger.info(
        "Copies : « %s » copié %d fois de suite, la première copie rendue privée",
        source.name,
        len(copies),
    )
    return len(copies)
