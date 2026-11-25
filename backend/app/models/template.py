import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, false, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.constants.templates import (
    FREE_PLAN_MAX_TILES,
    OFFICIAL_ACCOUNT_ID,
    OFFICIAL_TEMPLATE_MAX_TAGS,
    OFFICIAL_TEMPLATE_MAX_TILES,
    TEMPLATE_MAX_TAGS,
    TEMPLATE_NAME_MAX_LENGTH,
)
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import TemplateModeration, TemplateVisibility

if TYPE_CHECKING:
    from app.models.template_ancestor import TemplateAncestor
    from app.models.template_tag import TemplateTag
    from app.models.tier import Tier
    from app.models.tile import Tile
    from app.models.user import User


LISTED_CANDIDATES = text(
    f"visibility = '{TemplateVisibility.PUBLIC}' "
    f"AND moderation = '{TemplateModeration.NONE}' AND deleted_at IS NULL"
)


class Template(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (
        Index(
            "ix_templates_listed_search",
            func.to_tsvector(text("'simple'"), text("search_text")),
            postgresql_using="gin",
            postgresql_where=LISTED_CANDIDATES,
        ),
        Index(
            "ix_templates_listed_newest",
            text("first_made_public_at DESC"),
            text("id DESC"),
            postgresql_where=LISTED_CANDIDATES,
        ),
        Index(
            "ix_templates_deleted",
            "deleted_at",
            "id",
            postgresql_where=text("deleted_at IS NOT NULL"),
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
    deletion_reason: Mapped[str | None] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
    visibility: Mapped[TemplateVisibility] = mapped_column(
        text_enum(TemplateVisibility, "template_visibility"),
        default=TemplateVisibility.PRIVATE,
        server_default=text("'private'"),
    )
    first_made_public_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_text: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    featured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    editing_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    editing_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    edit_logged: Mapped[bool] = mapped_column(default=False, server_default=false())
    forks_allowed: Mapped[bool] = mapped_column(default=False, server_default=false())

    editing_by: Mapped[User | None] = relationship(foreign_keys=[editing_by_id])

    tiers: Mapped[list[Tier]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tier.position"
    )
    tiles: Mapped[list[Tile]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tile.position"
    )
    tags: Mapped[list[TemplateTag]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateTag.position"
    )
    ancestors: Mapped[list[TemplateAncestor]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateAncestor.depth",
        foreign_keys="TemplateAncestor.template_id",
    )

    @property
    def is_official(self) -> bool:
        return self.owner_id == OFFICIAL_ACCOUNT_ID

    @property
    def max_tiles(self) -> int:
        return OFFICIAL_TEMPLATE_MAX_TILES if self.is_official else FREE_PLAN_MAX_TILES

    @property
    def max_tags(self) -> int:
        return OFFICIAL_TEMPLATE_MAX_TAGS if self.is_official else TEMPLATE_MAX_TAGS

    @property
    def fits_player_limits(self) -> bool:
        return len(self.tiles) <= FREE_PLAN_MAX_TILES and len(self.tags) <= TEMPLATE_MAX_TAGS

    @property
    def copy_allowed(self) -> bool:
        return self.forks_allowed and self.fits_player_limits

    def active_editor(self, now: datetime) -> User | None:
        if self.editing_until is None or self.editing_until <= now:
            return None
        return self.editing_by
