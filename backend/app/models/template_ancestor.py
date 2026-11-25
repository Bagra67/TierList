import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.template import Template


class TemplateAncestor(Base):
    __tablename__ = "template_ancestors"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True
    )
    depth: Mapped[int] = mapped_column(primary_key=True)
    ancestor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), index=True
    )
    ancestor_name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))

    template: Mapped[Template] = relationship(
        back_populates="ancestors", foreign_keys=[template_id]
    )
