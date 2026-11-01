import uuid
from datetime import datetime

from sqlalchemy import Select, delete, exists, func, or_, select
from sqlalchemy.orm import Session
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
    """Image de n'importe quel auteur, quel que soit son statut, verrouillée jusqu'à la fin de
    la transaction : pour la modération."""
    return session.get(Image, image_id, with_for_update=True)


def is_fingerprint_banned(session: Session, sha256: str) -> bool:
    """Une image supprimée par la modération avait cette empreinte : le même fichier est refusé.
    Les lignes des images supprimées sont gardées pour cela (index ix_images_sha256)."""
    statement: Select[bool] = select(
        exists().where(Image.sha256 == sha256, Image.status == ImageStatus.DELETED)
    )
    return session.scalars(statement).one()


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
    """Supprime les images visibles créées avant limit qu'aucune tuile, de template ou de
    snapshot, n'utilise, en une seule requête ; renvoie leurs clés de stockage, pour effacer
    ensuite les fichiers.

    Une tuile qui rattacherait l'une de ces images au même moment attend la fin de la
    suppression, puis échoue sur la clé étrangère : aucune tuile ne pointe vers un fichier
    effacé. Les images masquées ou supprimées par la modération gardent leur ligne (#124)."""
    used_by_a_tile: Exists = exists().where(Tile.image_id == Image.id)
    # Une partie jouée garde ses images, même quand le template ne les utilise plus
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
) -> list[tuple[Image, str | None]]:
    """Images visibles ou masquées, des plus récentes aux plus anciennes, avec le nom de leur
    auteur (None une fois son compte supprimé). Filtres : un texte cherché sans casse dans le nom
    ou l'e-mail de l'auteur (% et _ y sont des caractères ordinaires), une période d'envoi et un
    statut. Les images supprimées n'ont plus de fichier : elles n'y sont jamais (index
    ix_images_created_at)."""
    statement: Select[Image, str] = (
        select(Image, User.display_name)
        .outerjoin(User, User.id == Image.owner_id)
        .where(Image.status != ImageStatus.DELETED)
    )
    if status is not None:
        statement = statement.where(Image.status == status)
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
    # Jointure externe : le nom est None pour une image dont l'auteur a supprimé son compte
    return [(image, display_name) for image, display_name in session.execute(statement).all()]


def template_names_by_image(
    session: Session, image_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Noms des modèles, non supprimés, dont une tuile montre chacune de ces images, par ordre
    alphabétique ; une image sans modèle n'a pas de clé."""
    statement: Select[uuid.UUID | None, str] = (
        select(Tile.image_id, Template.name)
        .join(Template, Template.id == Tile.template_id)
        .where(Tile.image_id.in_(image_ids), Template.deleted_at.is_(None))
        .distinct()
        .order_by(Tile.image_id, Template.name)
    )
    names: dict[uuid.UUID, list[str]] = {}
    for image_id, name in session.execute(statement).all():
        # Jamais None : le filtre ne garde que les tuiles de ces images
        if image_id is not None:
            names.setdefault(image_id, []).append(name)
    return names


def game_counts_by_image(session: Session, image_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Nombre de parties (en cours ou terminées) jouées sur une version figée qui montre chacune de
    ces images ; une image jamais jouée n'a pas de clé."""
    statement: Select[uuid.UUID | None, int] = (
        select(SnapshotTile.image_id, func.count(func.distinct(Game.id)))
        .join(Game, Game.snapshot_id == SnapshotTile.snapshot_id)
        .where(SnapshotTile.image_id.in_(image_ids))
        .group_by(SnapshotTile.image_id)
    )
    # Jamais None : le filtre ne garde que les tuiles de ces images
    return {
        image_id: count
        for image_id, count in session.execute(statement).all()
        if image_id is not None
    }
