import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import ReturningDelete, ReturningUpdate

from app.models.enums import ModerationTargetType, ReportStatus
from app.models.report import Report


@dataclass(frozen=True)
class OpenReportGroup:
    target_type: ModerationTargetType
    target_id: uuid.UUID
    report_count: int
    first_reported_at: datetime


def add_report(session: Session, report: Report) -> None:
    session.add(report)


def count_reports_of_account_since(
    session: Session, reporter_id: uuid.UUID, since: datetime
) -> int:
    statement: Select[int] = select(func.count(Report.id)).where(
        Report.reporter_id == reporter_id, Report.created_at >= since
    )
    return session.scalar(statement) or 0


def count_reports_of_browser_since(session: Session, browser_hash: str, since: datetime) -> int:
    statement: Select[int] = select(func.count(Report.id)).where(
        Report.reporter_browser_hash == browser_hash, Report.created_at >= since
    )
    return session.scalar(statement) or 0


def list_open_report_groups(
    session: Session, limit: int, offset: int, owner_id: uuid.UUID | None
) -> list[OpenReportGroup]:
    report_count = func.count(Report.id)
    first_reported_at = func.min(Report.created_at)
    statement = (
        select(Report.target_type, Report.target_id, report_count, first_reported_at)
        .where(Report.status == ReportStatus.OPEN)
        .group_by(Report.target_type, Report.target_id)
        .order_by(report_count.desc(), first_reported_at, Report.target_id)
        .limit(limit)
        .offset(offset)
    )
    if owner_id is not None:
        statement = statement.where(Report.owner_id == owner_id)
    return [
        OpenReportGroup(target_type, target_id, count, first_at)
        for target_type, target_id, count, first_at in session.execute(statement).all()
    ]


def count_open_report_groups(session: Session) -> int:
    groups = (
        select(Report.target_type, Report.target_id)
        .where(Report.status == ReportStatus.OPEN)
        .group_by(Report.target_type, Report.target_id)
        .subquery()
    )
    statement: Select[int] = select(func.count()).select_from(groups)
    return session.scalar(statement) or 0


def list_open_reports_of_targets(session: Session, target_ids: list[uuid.UUID]) -> list[Report]:
    statement: Select[Report] = (
        select(Report)
        .where(Report.status == ReportStatus.OPEN, Report.target_id.in_(target_ids))
        .order_by(Report.created_at, Report.id)
    )
    return list(session.scalars(statement).all())


def list_open_reports_of_target_for_update(
    session: Session, target_type: ModerationTargetType, target_id: uuid.UUID
) -> list[Report]:
    statement: Select[Report] = (
        select(Report)
        .where(
            Report.status == ReportStatus.OPEN,
            Report.target_type == target_type,
            Report.target_id == target_id,
        )
        .order_by(Report.created_at, Report.id)
        .with_for_update()
    )
    return list(session.scalars(statement).all())


def close_open_reports(
    session: Session,
    target_type: ModerationTargetType,
    target_ids: list[uuid.UUID],
    status: ReportStatus,
    action_id: uuid.UUID,
) -> int:
    statement: ReturningUpdate[uuid.UUID] = (
        update(Report)
        .where(
            Report.status == ReportStatus.OPEN,
            Report.target_type == target_type,
            Report.target_id.in_(target_ids),
        )
        .values(status=status, closed_at=datetime.now(UTC), closed_by_action_id=action_id)
        .returning(Report.id)
        .execution_options(synchronize_session=False)
    )
    return len(session.scalars(statement).all())


def delete_reports_closed_before(session: Session, limit: datetime) -> int:
    statement: ReturningDelete[uuid.UUID] = (
        delete(Report)
        .where(Report.status != ReportStatus.OPEN, Report.closed_at < limit)
        .returning(Report.id)
    )
    return len(session.scalars(statement).all())
