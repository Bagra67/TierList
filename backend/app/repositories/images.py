import uuid
from datetime import datetime

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import ReturningDelete
from sqlalchemy.sql.expression import Exists

from app.models.image import Image, ImageStatus
from app.models.tile import Tile


def add_image(session: Session, image: Image) -> None:
    session.add(image)


def get_owned_image(session: Session, image_id: uuid.UUID, owner_id: uuid.UUID) -> Image | None:
    """Image visible de cet auteur : une image masquée par la modération ne peut plus être
    rattachée à une tuile."""
    statement: Select[Image] = select(Image).where(
        Image.id == image_id,
        Image.owner_id == owner_id,
        Image.status == ImageStatus.VISIBLE,
    )
    return session.scalars(statement).one_or_none()


def count_images_created_since(session: Session, owner_id: uuid.UUID, since: datetime) -> int:
    """Nombre d'images envoyées par cet auteur depuis since (index owner_id, created_at)."""
    statement: Select[int] = select(func.count(Image.id)).where(
        Image.owner_id == owner_id, Image.created_at >= since
    )
    return session.scalars(statement).one()


def delete_unused_images_created_before(session: Session, limit: datetime) -> list[str]:
    """Supprime les images visibles créées avant limit qu'aucune tuile n'utilise, en une seule
    requête ; renvoie leurs clés de stockage, pour effacer ensuite les fichiers.

    Une tuile qui rattacherait l'une de ces images au même moment attend la fin de la
    suppression, puis échoue sur la clé étrangère : aucune tuile ne pointe vers un fichier
    effacé. Les images masquées ou supprimées par la modération gardent leur ligne (#124)."""
    used_by_a_tile: Exists = exists().where(Tile.image_id == Image.id)
    statement: ReturningDelete[str] = (
        delete(Image)
        .where(
            Image.created_at < limit,
            Image.status == ImageStatus.VISIBLE,
            ~used_by_a_tile,
        )
        .returning(Image.storage_key)
    )
    return list(session.scalars(statement).all())
