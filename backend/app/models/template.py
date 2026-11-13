import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.constants.templates import FREE_PLAN_MAX_TILES, TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import TemplateModeration, TemplateVisibility

if TYPE_CHECKING:
    from app.models.template_tag import TemplateTag
    from app.models.tier import Tier
    from app.models.tile import Tile


class Template(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (
        Index(
            "ix_templates_listed_search",
            func.to_tsvector(text("'simple'"), text("search_text")),
            postgresql_using="gin",
            postgresql_where=text(
                f"visibility = '{TemplateVisibility.PUBLIC}' "
                f"AND moderation = '{TemplateModeration.NONE}' AND deleted_at IS NULL"
            ),
        ),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    moderation: Mapped[TemplateModeration] = mapped_column(
        text_enum(TemplateModeration, "template_moderation"),
        default=TemplateModeration.NONE,
        server_default=text("'none'"),
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
    visibility: Mapped[TemplateVisibility] = mapped_column(
        text_enum(TemplateVisibility, "template_visibility"),
        default=TemplateVisibility.PRIVATE,
        server_default=text("'private'"),
    )
    first_made_public_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_text: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))

    tiers: Mapped[list[Tier]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tier.position"
    )
    tiles: Mapped[list[Tile]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tile.position"
    )
    tags: Mapped[list[TemplateTag]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateTag.position"
    )

    @property
    def max_tiles(self) -> int:
        return FREE_PLAN_MAX_TILES
