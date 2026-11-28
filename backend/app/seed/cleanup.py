import hashlib
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import Session

from app.constants.templates import OFFICIAL_ACCOUNT_ID
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.report import Report
from app.models.snapshot_tile import SnapshotTile
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.tile import Tile
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

    seed_official_template_ids = select(ModerationAction.target_id).where(
        ModerationAction.actor_id.in_(seed_user_ids),
        ModerationAction.action == ModerationActionKind.CREATE,
        ModerationAction.target_type == ModerationTargetType.TEMPLATE,
    )
    session.execute(
        delete(Template).where(
            Template.owner_id == OFFICIAL_ACCOUNT_ID, Template.id.in_(seed_official_template_ids)
        )
    )
    session.execute(delete(ModerationAction).where(ModerationAction.actor_id.in_(seed_user_ids)))
    session.execute(
        delete(Report).where(
            or_(Report.reporter_id.in_(seed_user_ids), Report.owner_id.in_(seed_user_ids))
        )
    )
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
    seed_template_ids = select(Template.id).where(Template.owner_id.in_(seed_user_ids))
    session.execute(
        delete(TemplateSnapshot).where(TemplateSnapshot.template_id.in_(seed_template_ids))
    )
    seed_image_ids: list[uuid.UUID] = list(
        session.scalars(select(Image.id).where(Image.owner_id.in_(seed_user_ids))).all()
    )
    session.execute(delete(User).where(User.id.in_(seed_user_ids)))
    images: list[tuple[uuid.UUID, str | None]] = [
        (image_id, _file_key(storage_key, status))
        for image_id, storage_key, status in session.execute(
            select(Image.id, Image.storage_key, Image.status).where(
                Image.id.in_(seed_image_ids),
                ~exists().where(Tile.image_id == Image.id),
                ~exists().where(SnapshotTile.image_id == Image.id),
            )
        ).all()
    ]
    deleted_image_ids: set[uuid.UUID] = {image_id for image_id, _ in images}
    session.execute(delete(Image).where(Image.id.in_(deleted_image_ids)))
    kept_image_ids: list[uuid.UUID] = [
        image_id for image_id in seed_image_ids if image_id not in deleted_image_ids
    ]
    _unban_fingerprints_the_seed_uploads_again(session, kept_image_ids)
    session.commit()
    if kept_image_ids:
        logger.info(
            "Images seed gardées, utilisées par des copies d'autres comptes : %d",
            len(kept_image_ids),
        )
    logger.info("Données seed supprimées en base : %d parties, %d images", games, len(images))
    _delete_image_files_after_commit(storage, images)
    return SeedCleanup(accounts=len(seed_user_ids), games=games, images=len(images))


def _unban_fingerprints_the_seed_uploads_again(
    session: Session, kept_image_ids: list[uuid.UUID]
) -> None:
    for image in session.scalars(
        select(Image).where(Image.id.in_(kept_image_ids), Image.status == ImageStatus.DELETED)
    ):
        image.sha256 = hashlib.sha256(image.id.bytes).hexdigest()


def _delete_image_files_after_commit(
    storage: ImageStorage, images: list[tuple[uuid.UUID, str | None]]
) -> None:
    for number, (_, file_key) in enumerate(images, start=1):
        if file_key is not None:
            storage.delete(file_key)
        if number % 25 == 0 or number == len(images):
            logger.info("Fichiers d'images effacés : %d/%d", number, len(images))


def _file_key(storage_key: str, status: ImageStatus) -> str | None:
    match status:
        case ImageStatus.VISIBLE:
            return storage_key
        case ImageStatus.HIDDEN:
            return quarantine_key(storage_key)
        case ImageStatus.DELETED:
            return None
