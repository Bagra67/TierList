import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.images import IMAGE_SHA256_LENGTH, IMAGE_STORAGE_KEY_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ImageStatus(StrEnum):
    """Statut de modération (#124) : toute image envoyée est visible."""

    VISIBLE = "visible"
    HIDDEN = "hidden"
    DELETED = "deleted"


class Image(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une image compressée, stockée dans le bucket S3 sous storage_key.

    Immuable : remplacer l'image d'une tuile crée une nouvelle image, un fichier stocké n'est
    jamais réécrit (docs/technical/images.md).
    """

    __tablename__ = "images"
    __table_args__ = (
        # Limite d'envois par compte et par heure : compte les images récentes d'un auteur
        Index("ix_images_owner_id_created_at", "owner_id", "created_at"),
    )

    # Toute image a un auteur connu : seuls les comptes en envoient
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Clé aléatoire ({uuid}.webp) : l'URL publique est impossible à deviner
    storage_key: Mapped[str] = mapped_column(String(IMAGE_STORAGE_KEY_MAX_LENGTH), unique=True)
    width: Mapped[int]
    height: Mapped[int]
    # Taille du fichier stocké (WebP), pas celle du fichier reçu
    size_bytes: Mapped[int]
    # Empreinte du fichier reçu : permettra de refuser le renvoi d'un fichier banni (#124)
    sha256: Mapped[str] = mapped_column(String(IMAGE_SHA256_LENGTH), index=True)
    status: Mapped[ImageStatus] = mapped_column(
        Enum(
            ImageStatus,
            name="image_status",
            # Colonne texte avec une contrainte CHECK plutôt qu'un type ENUM PostgreSQL : ajouter
            # un statut ne demande pas d'ALTER TYPE
            native_enum=False,
            create_constraint=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=ImageStatus.VISIBLE,
    )
