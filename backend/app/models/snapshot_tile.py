import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TILE_TEXT_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.image import Image
    from app.models.template_snapshot import TemplateSnapshot


class SnapshotTile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "snapshot_tiles"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("template_snapshots.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str | None] = mapped_column(String(TILE_TEXT_MAX_LENGTH))
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("images.id"), index=True)
    position: Mapped[int]

    snapshot: Mapped[TemplateSnapshot] = relationship(back_populates="tiles")
    image: Mapped[Image | None] = relationship(lazy="selectin")
