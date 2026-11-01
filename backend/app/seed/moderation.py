"""Entrées du journal de modération du jeu de données, écrites par le vrai service, puis datées
dans le passé. Leurs cibles sont des modèles, des comptes et des pseudos du jeu de données."""

import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.user import User
from app.seed.games import GUEST_NICKNAMES
from app.services.moderation_log import ModerationLogService

# Les entrées sont étalées sur cette durée
LOG_SPAN_DAYS = 120
REASONS: tuple[str, ...] = (
    "Harcèlement", "Contenu à caractère sexuel", "Propos haineux", "Spam", "Droit d'auteur",
    "Pseudo insultant", "Aucun manquement", "Signalement abusif", "Récidive",
    "Image sans rapport avec le modèle", "Données personnelles visibles", "Contenu violent",
)  # fmt: skip


def create_moderation_log(
    session: Session,
    settings: Settings,
    count: int,
    super_admins: list[User],
    accounts: list[User],
    templates: list[Template],
    rng: random.Random,
) -> list[ModerationAction]:
    log: ModerationLogService = ModerationLogService(session, settings)
    entries: list[ModerationAction] = []
    for index in range(count):
        target_type: ModerationTargetType = rng.choice(list(ModerationTargetType))
        target_id, target_label = _target(target_type, accounts, templates, rng)
        entry: ModerationAction = log.record(
            rng.choice(super_admins),
            rng.choice(list(ModerationActionKind)),
            target_type,
            target_id,
            target_label,
            rng.choice(REASONS),
        )
        # De la plus ancienne à la plus récente, sur LOG_SPAN_DAYS
        days_ago: float = LOG_SPAN_DAYS * (count - index) / count
        entry.created_at = datetime.now(UTC) - timedelta(days=days_ago, minutes=rng.randint(0, 600))
        entries.append(entry)
    # record ne valide pas la transaction : c'est l'appelant qui la valide, comme une action
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
