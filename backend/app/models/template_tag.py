import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.templates import TAG_MAX_LENGTH
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.template import Template


class TemplateTag(Base):
    __tablename__ = "template_tags"

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True
    )
    normalized_label: Mapped[str] = mapped_column(Text, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(TAG_MAX_LENGTH))
    position: Mapped[int]

    template: Mapped[Template] = relationship(back_populates="tags")
