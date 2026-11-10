import logging
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.user import User
from app.seed.no_op import NoOpRoomEventPublisher
from app.seed.seats import GUEST_NICKNAMES
from app.services.account_bans import AccountBanService
from app.services.image_moderation import ImageModerationService
from app.services.image_storage import ImageStorage
from app.services.moderation_log import ModerationLogService
from app.services.template_moderation import TemplateModerationService

logger = logging.getLogger(__name__)

LOG_SPAN_DAYS = 120
REASONS: tuple[str, ...] = (
    "Harcèlement", "Contenu à caractère sexuel", "Propos haineux", "Spam", "Droit d'auteur",
    "Pseudo insultant", "Aucun manquement", "Signalement abusif", "Récidive",
    "Image sans rapport avec le modèle", "Données personnelles visibles", "Contenu violent",
)  # fmt: skip
BAN_REASONS: tuple[str, ...] = (
    "Harcèlement répété", "Spam", "Propos haineux", "Usurpation d'identité",
)  # fmt: skip
TEMPORARY_BAN_DAYS = 14
BAN_LIFT_REASON = "Recours accepté"
TEMPLATE_REASONS: tuple[str, ...] = (
    "Harcèlement", "Propos haineux", "Données personnelles visibles", "Droit d'auteur",
)  # fmt: skip
IMAGE_REASONS: tuple[str, ...] = (
    "Contenu violent", "Contenu à caractère sexuel", "Droit d'auteur",
    "Données personnelles visibles", "Image sans rapport avec le modèle",
)  # fmt: skip


def create_moderation_log(
    session: Session,
    count: int,
    super_admins: list[User],
    accounts: list[User],
    templates: list[Template],
    rng: random.Random,
) -> list[ModerationAction]:
    entries: list[ModerationAction] = []
    for index in range(count):
        target_type: ModerationTargetType = rng.choice(list(ModerationTargetType))
        target_id, target_label = _target(target_type, accounts, templates, rng)
        actor: User = rng.choice(super_admins)
        days_ago: float = LOG_SPAN_DAYS * (count - index) / count
        entries.append(
            ModerationAction(
                created_at=datetime.now(UTC)
                - timedelta(days=days_ago, minutes=rng.randint(0, 600)),
                actor_id=actor.id,
                actor_name=actor.display_name,
                action=rng.choice(list(ModerationActionKind)),
                target_type=target_type,
                target_id=target_id,
                target_label=target_label,
                reason=rng.choice(REASONS),
            )
        )
        if (index + 1) % 30 == 0 or index + 1 == count:
            logger.info("Journal de modération : %d/%d entrées", index + 1, count)
    session.add_all(entries)
    session.commit()
    return entries


def _target(
    target_type: ModerationTargetType,
    accounts: list[User],
    templates: list[Template],
    rng: random.Random,
) -> tuple[uuid.UUID | None, str]:
    match target_type:
        case ModerationTargetType.TEMPLATE:
            template: Template = rng.choice(templates)
            return template.id, template.name
        case ModerationTargetType.ACCOUNT:
            account: User = rng.choice(accounts)
            return account.id, account.display_name
        case ModerationTargetType.NICKNAME:
            return None, rng.choice(GUEST_NICKNAMES)
        case ModerationTargetType.IMAGE:
            return None, f"image-{rng.randint(1, 999)}.png"
        case ModerationTargetType.GAME:
            return None, f"Partie « {rng.choice(templates).name} »"


def moderate_images(
    session: Session,
    settings: Settings,
    storage: ImageStorage,
    super_admins: list[User],
    images: list[Image],
    hidden: int,
    deleted: int,
    rng: random.Random,
) -> int:
    service: ImageModerationService = ImageModerationService(
        session, storage, ModerationLogService(session, settings)
    )
    chosen: list[Image] = rng.sample(images, hidden + deleted)
    for image in chosen[:hidden]:
        service.hide(rng.choice(super_admins), image.id, rng.choice(IMAGE_REASONS))
    for image in chosen[hidden:]:
        service.delete(rng.choice(super_admins), image.id, rng.choice(IMAGE_REASONS))
    logger.info("Images modérées : %d masquées, %d supprimées", hidden, deleted)
    return len(chosen)


def moderate_templates(
    session: Session,
    settings: Settings,
    super_admins: list[User],
    template_ids_to_hide: list[uuid.UUID],
    template_ids_to_delete: list[uuid.UUID],
    rng: random.Random,
) -> int:
    service: TemplateModerationService = TemplateModerationService(
        session, ModerationLogService(session, settings)
    )
    for template_id in template_ids_to_hide:
        service.hide(rng.choice(super_admins), template_id, rng.choice(TEMPLATE_REASONS))
    for template_id in template_ids_to_delete:
        service.delete(rng.choice(super_admins), template_id, rng.choice(TEMPLATE_REASONS))
    logger.info(
        "Modèles modérés : %d masqués, %d supprimés",
        len(template_ids_to_hide),
        len(template_ids_to_delete),
    )
    return len(template_ids_to_hide) + len(template_ids_to_delete)


def ban_accounts(
    session: Session,
    settings: Settings,
    super_admins: list[User],
    temporarily: list[User],
    permanently: list[User],
    lifted: list[User],
    rng: random.Random,
) -> int:
    service: AccountBanService = AccountBanService(
        session, ModerationLogService(session, settings), NoOpRoomEventPublisher()
    )
    ends_at: datetime = datetime.now(UTC) + timedelta(days=TEMPORARY_BAN_DAYS)
    for user in temporarily:
        service.ban(rng.choice(super_admins), user.id, rng.choice(BAN_REASONS), ends_at)
    for user in permanently:
        service.ban(rng.choice(super_admins), user.id, rng.choice(BAN_REASONS), None)
    for user in lifted:
        super_admin: User = rng.choice(super_admins)
        service.ban(super_admin, user.id, rng.choice(BAN_REASONS), None)
        service.lift(super_admin, user.id, BAN_LIFT_REASON)
    logger.info(
        "Comptes bannis : %d temporairement, %d définitivement, %d puis graciés",
        len(temporarily),
        len(permanently),
        len(lifted),
    )
    return len(temporarily) + len(permanently) + 2 * len(lifted)
