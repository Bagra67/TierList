import uuid
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.report import Report


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
