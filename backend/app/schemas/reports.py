import uuid
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.constants.reports import REPORT_DETAILS_MAX_LENGTH
from app.models.enums import ReportReason, ReportTargetKind

ReportDetails = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=REPORT_DETAILS_MAX_LENGTH)
]


class CreateReportRequest(BaseModel):
    """A report (US-1.2). target_id designates, depending on target_kind: an item of a game, a
    participant of a room, a player of the results or a closed game."""

    target_kind: ReportTargetKind
    target_id: uuid.UUID
    reason: ReportReason
    details: ReportDetails | None = None


class ReportResponse(BaseModel):
    """The saved report. It tells nothing about its author."""

    id: uuid.UUID
