import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.seed.accounts import SEED_EMAIL_DOMAIN, SEED_EMAIL_PREFIX
from app.services.image_storage import ImageStorage, quarantine_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeedCleanup:
    accounts: int
    games: int
    images: int


def delete_seed_data(session: Session, storage: ImageStorage) -> SeedCleanup:
    seed_user_ids: list[uuid.UUID] = list(
        session.scalars(
            select(User.id).where(
                User.email.startswith(SEED_EMAIL_PREFIX, autoescape=True),
                User.email.endswith(SEED_EMAIL_DOMAIN, autoescape=True),
            )
        ).all()
    )
    if not seed_user_ids:
        logger.info("Aucune donnée seed à supprimer")
        return SeedCleanup(accounts=0, games=0, images=0)
    logger.info("Suppression des données seed : %d comptes", len(seed_user_ids))

    session.execute(delete(ModerationAction).where(ModerationAction.actor_id.in_(seed_user_ids)))
    games: int = len(
        session.scalars(
            delete(Game)
            .where(
                or_(
                    Game.admin_id.in_(seed_user_ids),
                    exists().where(
                        GamePlayer.game_id == Game.id, GamePlayer.user_id.in_(seed_user_ids)
                    ),
                )
            )
            .returning(Game.id)
        ).all()
    )
    # 3. Les instantanés des modèles seed, que plus aucune partie n'utilise : leur modèle
    # passerait à NULL
    seed_template_ids = select(Template.id).where(Template.owner_id.in_(seed_user_ids))
    session.execute(
        delete(TemplateSnapshot).where(TemplateSnapshot.template_id.in_(seed_template_ids))
    )
    images: list[tuple[uuid.UUID, str | None]] = [
        (image_id, _file_key(storage_key, status))
        for image_id, storage_key, status in session.execute(
            select(Image.id, Image.storage_key, Image.status).where(
                Image.owner_id.in_(seed_user_ids)
            )
        ).all()
    ]
    session.execute(delete(User).where(User.id.in_(seed_user_ids)))
    session.execute(delete(Image).where(Image.id.in_([image_id for image_id, _ in images])))
    session.commit()
    # Les fichiers après le commit : une erreur de stockage ne laisse pas d'image sans fichier
    logger.info("Données seed supprimées en base : %d parties, %d images", games, len(images))
    for number, (_, file_key) in enumerate(images, start=1):
        if file_key is not None:
            storage.delete(file_key)
        if number % 25 == 0 or number == len(images):
            logger.info("Fichiers d'images effacés : %d/%d", number, len(images))
    return SeedCleanup(accounts=len(seed_user_ids), games=games, images=len(images))


def _file_key(storage_key: str, status: ImageStatus) -> str | None:
    match status:
        case ImageStatus.VISIBLE:
            return storage_key
        case ImageStatus.HIDDEN:
            return quarantine_key(storage_key)
        case ImageStatus.DELETED:
            return None
