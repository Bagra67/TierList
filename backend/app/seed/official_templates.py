import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateVisibility
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.repositories import users as user_repository
from app.services.moderation_log import ModerationLogService
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)

OFFICIAL_THEMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Fromages de France",
        (
            "Comté", "Roquefort", "Camembert", "Brie de Meaux", "Reblochon", "Munster",
            "Beaufort", "Saint-Nectaire", "Époisses", "Cantal", "Mont d'Or", "Maroilles",
        ),
    ),
    (
        "Jeux de société",
        (
            "Échecs", "Dames", "Scrabble", "Monopoly", "Uno", "Dixit", "Carcassonne",
            "Les Aventuriers du Rail", "Codenames", "Catan", "Dobble", "Time's Up",
        ),
    ),
    (
        "Desserts du monde",
        (
            "Tiramisu", "Crème brûlée", "Baklava", "Mochi", "Churros", "Cheesecake",
            "Pavlova", "Tarte Tatin", "Brownie", "Pastel de nata",
        ),
    ),
)  # fmt: skip


def create_official_templates(
    session: Session, settings: Settings, super_admins: list[User], count: int
) -> int:
    if count > len(OFFICIAL_THEMES):
        raise ValueError(f"The seed has {len(OFFICIAL_THEMES)} official templates at most")
    official_account: User = user_repository.get_official_account(session)
    moderation_log: ModerationLogService = ModerationLogService(session, settings)
    templates: TemplateService = TemplateService(session, settings, moderation_log)
    now: datetime = datetime.now(UTC)
    log_entries: int = 0
    for index, (name, items) in enumerate(OFFICIAL_THEMES[:count]):
        super_admin: User = super_admins[index % len(super_admins)]
        template: Template = templates.add_new(official_account, name)
        template.tiles = [Tile(text=text, position=position) for position, text in enumerate(items)]
        actions: list[ModerationActionKind] = [ModerationActionKind.CREATE]
        is_last_kept_as_draft: bool = index == count - 1
        if not is_last_kept_as_draft:
            template.visibility = TemplateVisibility.PUBLIC
            template.first_made_public_at = now
            actions.append(ModerationActionKind.PUBLISH)
        if index == 0 and not is_last_kept_as_draft:
            template.featured_at = now
            actions.append(ModerationActionKind.FEATURE)
        for action in actions:
            moderation_log.record(
                super_admin, action, ModerationTargetType.TEMPLATE, template.id, name, reason=None
            )
        log_entries += len(actions)
    session.commit()
    logger.info("Modèles officiels : %d", count)
    return log_entries
