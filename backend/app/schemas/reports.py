import uuid
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.constants.reports import REPORT_DETAILS_MAX_LENGTH
from app.models.enums import ReportReason, ReportTargetKind

ReportDetails = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=REPORT_DETAILS_MAX_LENGTH)
]


class CreateReportRequest(BaseModel):
    """Un signalement (US-1.2). target_id désigne, selon target_kind : un item d'une partie, un
    participant d'une salle, un joueur des résultats ou une partie close."""

    target_kind: ReportTargetKind
    target_id: uuid.UUID
    reason: ReportReason
    details: ReportDetails | None = None


class ReportResponse(BaseModel):
    """Le signalement enregistré. Il ne dit rien de son auteur."""

    id: uuid.UUID
