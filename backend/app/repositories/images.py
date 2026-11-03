import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import Select, delete, exists, func, or_, select
from sqlalchemy.orm import Mapped, Session
from sqlalchemy.sql.dml import ReturningDelete
from sqlalchemy.sql.expression import Exists

from app.models.game import Game
from app.models.image import Image, ImageStatus
from app.models.snapshot_tile import SnapshotTile
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User


def add_image(session: Session, image: Image) -> None:
    session.add(image)


def get_image_for_update(session: Session, image_id: uuid.UUID) -> Image | None:
    return session.get(Image, image_id, with_for_update=True)


def is_fingerprint_banned(session: Session, sha256: str) -> bool:
    statement: Select[bool] = select(
        exists().where(Image.sha256 == sha256, Image.status == ImageStatus.DELETED)
    )
    return session.scalars(statement).one()


def get_owned_image(session: Session, image_id: uuid.UUID, owner_id: uuid.UUID) -> Image | None:
    statement: Select[Image] = select(Image).where(
        Image.id == image_id,
        Image.owner_id == owner_id,
        Image.status == ImageStatus.VISIBLE,
    )
    return session.scalars(statement).one_or_none()


def count_images_created_since(session: Session, owner_id: uuid.UUID, since: datetime) -> int:
    statement: Select[int] = select(func.count(Image.id)).where(
        Image.owner_id == owner_id, Image.created_at >= since
    )
    return session.scalars(statement).one()


def delete_unused_images_created_before(session: Session, limit: datetime) -> list[str]:
    """Supprime les images visibles créées avant limit qu'aucune tuile, de template ou de
    snapshot, n'utilise, en une seule requête ; renvoie leurs clés de stockage, pour effacer
    ensuite les fichiers.

    Une tuile qui rattacherait l'une de ces images au même moment attend la fin de la
    suppression, puis échoue sur la clé étrangère : aucune tuile ne pointe vers un fichier
    effacé. Les images masquées ou supprimées par la modération gardent leur ligne (#124)."""
    used_by_a_tile: Exists = exists().where(Tile.image_id == Image.id)
    used_by_a_snapshot: Exists = exists().where(SnapshotTile.image_id == Image.id)
    statement: ReturningDelete[str] = (
        delete(Image)
        .where(
            Image.created_at < limit,
            Image.status == ImageStatus.VISIBLE,
            ~used_by_a_tile,
            ~used_by_a_snapshot,
        )
        .returning(Image.storage_key)
    )
    return list(session.scalars(statement).all())


def list_recent_images(
    session: Session,
    limit: int,
    offset: int,
    author: str | None,
    created_after: datetime | None,
    created_before: datetime | None,
    status: ImageStatus | None,
    owner_id: uuid.UUID | None = None,
) -> list[tuple[Image, str | None]]:
    statement: Select[Image, str] = (
        select(Image, User.display_name)
        .outerjoin(User, User.id == Image.owner_id)
        .where(Image.status != ImageStatus.DELETED)
    )
    if status is not None:
        statement = statement.where(Image.status == status)
    if owner_id is not None:
        statement = statement.where(Image.owner_id == owner_id)
    if author:
        statement = statement.where(
            or_(
                User.display_name.icontains(author, autoescape=True),
                User.email.icontains(author, autoescape=True),
            )
        )
    if created_after is not None:
        statement = statement.where(Image.created_at >= created_after)
    if created_before is not None:
        statement = statement.where(Image.created_at < created_before)
    statement = (
        # L'identifiant départage deux images du même instant : une page ne saute rien
        statement.order_by(Image.created_at.desc(), Image.id).limit(limit).offset(offset)
    )
    return [(image, display_name) for image, display_name in session.execute(statement).all()]


def template_names_by_image(
    session: Session, image_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    image_id_kept_by_the_filter: Mapped[uuid.UUID] = cast(Mapped[uuid.UUID], Tile.image_id)
    statement: Select[uuid.UUID, str] = (
        select(image_id_kept_by_the_filter, Template.name)
        .join(Template, Template.id == Tile.template_id)
        .where(Tile.image_id.in_(image_ids), Template.deleted_at.is_(None))
        .distinct()
        .order_by(Tile.image_id, Template.name)
    )
    names: dict[uuid.UUID, list[str]] = {}
    for image_id, name in session.execute(statement).all():
        names.setdefault(image_id, []).append(name)
    return names


def game_counts_by_image(session: Session, image_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    image_id_kept_by_the_filter: Mapped[uuid.UUID] = cast(Mapped[uuid.UUID], SnapshotTile.image_id)
    statement: Select[uuid.UUID, int] = (
        select(image_id_kept_by_the_filter, func.count(func.distinct(Game.id)))
        .join(Game, Game.snapshot_id == SnapshotTile.snapshot_id)
        .where(SnapshotTile.image_id.in_(image_ids))
        .group_by(SnapshotTile.image_id)
    )
    return {image_id: count for image_id, count in session.execute(statement).all()}


def list_visible_image_ids_of_owner(session: Session, owner_id: uuid.UUID) -> list[uuid.UUID]:
    statement: Select[uuid.UUID] = (
        select(Image.id)
        .where(Image.owner_id == owner_id, Image.status == ImageStatus.VISIBLE)
        .order_by(Image.created_at, Image.id)
    )
    return list(session.scalars(statement).all())
