import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.constants.templates import FREE_PLAN_MAX_TILES, TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import TemplateModeration

if TYPE_CHECKING:
    from app.models.tier import Tier
    from app.models.tile import Tile


class Template(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "templates"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    moderation: Mapped[TemplateModeration] = mapped_column(
        text_enum(TemplateModeration, "template_moderation"),
        default=TemplateModeration.NONE,
        server_default=text("'none'"),
    )
    # Motif du masquage, montré au propriétaire. Copié ici : le journal de modération est purgé
    # après 3 ans, un modèle peut rester masqué plus longtemps
    moderation_reason: Mapped[str | None] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))

    tiers: Mapped[list[Tier]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tier.position"
    )
    tiles: Mapped[list[Tile]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tile.position"
    )

    @property
    def max_tiles(self) -> int:
        return FREE_PLAN_MAX_TILES
