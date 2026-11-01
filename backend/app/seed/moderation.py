"""Modération du jeu de données : le journal, et quelques images masquées ou supprimées.

Les entrées du journal sont datées dans le passé. Leurs cibles sont des modèles, des comptes et des
pseudos du jeu de données. Elles sont écrites directement, comme ModerationLogService.record les
écrirait (auteur et libellé de la cible copiés), mais avec leur date d'emblée : record écrit chaque
entrée à part, et la redater ensuite coûterait deux requêtes par entrée, à travers Internet sur
staging.

Les images et les modèles modérés, peu nombreux, passent par les vrais services : le fichier d'une
image va en quarantaine ou est effacé, un modèle masqué ne lance plus de partie, et leur entrée du
journal désigne la vraie cible."""

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
from app.seed.seats import GUEST_NICKNAMES
from app.services.image_moderation import ImageModerationService
from app.services.image_storage import ImageStorage
from app.services.moderation_log import ModerationLogService
from app.services.template_moderation import TemplateModerationService

logger = logging.getLogger(__name__)

# Les entrées sont étalées sur cette durée
LOG_SPAN_DAYS = 120
REASONS: tuple[str, ...] = (
    "Harcèlement", "Contenu à caractère sexuel", "Propos haineux", "Spam", "Droit d'auteur",
    "Pseudo insultant", "Aucun manquement", "Signalement abusif", "Récidive",
    "Image sans rapport avec le modèle", "Données personnelles visibles", "Contenu violent",
)  # fmt: skip
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
        # De la plus ancienne à la plus récente, sur LOG_SPAN_DAYS
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
    """Identifiant et libellé d'une cible du jeu de données, de ce type."""
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
    """Masque hidden images et en supprime deleted autres, prises au hasard parmi celles des
    modèles à images ; renvoie le nombre d'actions écrites au journal."""
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
    template_ids: list[uuid.UUID],
    rng: random.Random,
) -> int:
    """Masque ces modèles ; renvoie le nombre d'actions écrites au journal."""
    service: TemplateModerationService = TemplateModerationService(
        session, ModerationLogService(session, settings)
    )
    for template_id in template_ids:
        service.hide(rng.choice(super_admins), template_id, rng.choice(TEMPLATE_REASONS))
    logger.info("Modèles masqués : %d", len(template_ids))
    return len(template_ids)
