import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions.reports import ReportsNotOpenError
from app.models.enums import ModerationActionKind, ModerationTargetType, ReportReason, ReportStatus
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.report import Report
from app.models.user import User
from app.repositories import games as game_repository
from app.repositories import images as image_repository
from app.repositories import reports as report_repository
from app.repositories import users as user_repository
from app.repositories.reports import OpenReportGroup
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportedContent:
    target_type: ModerationTargetType
    target_id: uuid.UUID
    label: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    report_count: int
    reasons: list[tuple[ReportReason, int]]
    details: list[str]
    first_reported_at: datetime
    image: Image | None
    public_token: str | None


@dataclass(frozen=True)
class ReportQueuePage:
    contents: list[ReportedContent]
    has_more: bool


class ReportQueueService:
    def __init__(
        self, session: Session, settings: Settings, moderation_log: ModerationLogService
    ) -> None:
        self._session = session
        self._settings = settings
        self._moderation_log = moderation_log

    def page(self, limit: int, offset: int, owner_id: uuid.UUID | None) -> ReportQueuePage:
        groups: list[OpenReportGroup] = report_repository.list_open_report_groups(
            self._session, limit + 1, offset, owner_id
        )
        shown_groups: list[OpenReportGroup] = groups[:limit]
        target_ids: list[uuid.UUID] = [group.target_id for group in shown_groups]
        reports_per_target: dict[tuple[ModerationTargetType, uuid.UUID], list[Report]] = {}
        for report in report_repository.list_open_reports_of_targets(self._session, target_ids):
            reports_per_target.setdefault((report.target_type, report.target_id), []).append(report)
        images: dict[uuid.UUID, Image] = image_repository.images_by_id(
            self._session, _targets_of_type(shown_groups, ModerationTargetType.IMAGE)
        )
        public_tokens: dict[uuid.UUID, str | None] = game_repository.public_tokens_by_game(
            self._session, _targets_of_type(shown_groups, ModerationTargetType.GAME)
        )
        owner_ids: list[uuid.UUID] = [
            report.owner_id
            for reports in reports_per_target.values()
            for report in reports
            if report.owner_id is not None
        ]
        owner_names: dict[uuid.UUID, str] = user_repository.display_names_by_id(
            self._session, owner_ids
        )
        contents: list[ReportedContent] = []
        for group in shown_groups:
            reports: list[Report] = reports_per_target[(group.target_type, group.target_id)]
            owner: uuid.UUID | None = reports[0].owner_id
            reasons: Counter[ReportReason] = Counter(report.reason for report in reports)
            contents.append(
                ReportedContent(
                    target_type=group.target_type,
                    target_id=group.target_id,
                    label=reports[0].target_label,
                    owner_id=owner,
                    owner_name=owner_names.get(owner) if owner is not None else None,
                    report_count=group.report_count,
                    reasons=reasons.most_common(),
                    details=[report.details for report in reports if report.details is not None],
                    first_reported_at=group.first_reported_at,
                    image=images.get(group.target_id),
                    public_token=public_tokens.get(group.target_id),
                )
            )
        return ReportQueuePage(contents=contents, has_more=len(groups) > limit)

    def count_open_contents(self) -> int:
        return report_repository.count_open_report_groups(self._session)

    def dismiss(
        self,
        super_admin: User,
        target_type: ModerationTargetType,
        target_id: uuid.UUID,
        reason: str,
    ) -> None:
        reports: list[Report] = report_repository.list_open_reports_of_target_for_update(
            self._session, target_type, target_id
        )
        if not reports:
            raise ReportsNotOpenError
        action: ModerationAction = self._moderation_log.record(
            super_admin,
            ModerationActionKind.DISMISS,
            target_type,
            target_id,
            reports[0].target_label or str(target_id),
            reason,
        )
        report_repository.close_open_reports(
            self._session, target_type, [target_id], ReportStatus.DISMISSED, action.id
        )
        self._session.commit()
        logger.info(
            "Signalements classés : target_type=%s target_id=%s super_admin_id=%s reports=%d",
            target_type,
            target_id,
            super_admin.id,
            len(reports),
        )

    def purge_closed(self) -> int:
        limit: datetime = datetime.now(UTC) - timedelta(
            days=self._settings.closed_report_retention_days
        )
        purged: int = report_repository.delete_reports_closed_before(self._session, limit)
        self._session.commit()
        logger.info("Signalements fermés purgés : %d (avant %s)", purged, limit.isoformat())
        return purged


def _targets_of_type(
    groups: list[OpenReportGroup], target_type: ModerationTargetType
) -> list[uuid.UUID]:
    return [group.target_id for group in groups if group.target_type == target_type]
