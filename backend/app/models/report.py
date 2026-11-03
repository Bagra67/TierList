import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.moderation import MODERATION_TARGET_LABEL_MAX_LENGTH
from app.constants.reports import (
    REPORT_DETAILS_MAX_LENGTH,
    REPORT_OPEN_BY_ACCOUNT_INDEX,
    REPORT_OPEN_BY_BROWSER_INDEX,
)
from app.constants.rooms import GUEST_TOKEN_HASH_LENGTH
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import ModerationTargetType, ReportReason, ReportStatus


class Report(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "reporter_id IS NULL OR reporter_browser_hash IS NULL",
            name="account_or_browser",
        ),
        Index(
            REPORT_OPEN_BY_ACCOUNT_INDEX,
            "target_type",
            "target_id",
            "reporter_id",
            unique=True,
            postgresql_where=text(f"status = '{ReportStatus.OPEN}'"),
        ),
        Index(
            REPORT_OPEN_BY_BROWSER_INDEX,
            "target_type",
            "target_id",
            "reporter_browser_hash",
            unique=True,
            postgresql_where=text(f"status = '{ReportStatus.OPEN}'"),
        ),
        Index("ix_reports_reporter_id_created_at", "reporter_id", "created_at"),
        Index("ix_reports_reporter_browser_hash_created_at", "reporter_browser_hash", "created_at"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reporter_browser_hash: Mapped[str | None] = mapped_column(String(GUEST_TOKEN_HASH_LENGTH))
    target_type: Mapped[ModerationTargetType] = mapped_column(
        text_enum(ModerationTargetType, "report_target_type")
    )
    target_id: Mapped[uuid.UUID]
    target_label: Mapped[str | None] = mapped_column(String(MODERATION_TARGET_LABEL_MAX_LENGTH))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reason: Mapped[ReportReason] = mapped_column(text_enum(ReportReason, "report_reason"))
    details: Mapped[str | None] = mapped_column(String(REPORT_DETAILS_MAX_LENGTH))
    status: Mapped[ReportStatus] = mapped_column(
        text_enum(ReportStatus, "report_status"), default=ReportStatus.OPEN
    )
