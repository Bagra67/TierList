from app.api.presenters.images import optional_image_url
from app.models.enums import ReportReason
from app.schemas.moderation import ReportedContentResponse, ReportReasonCountResponse
from app.services.image_storage import ImageStorage
from app.services.report_queue import ReportedContent


def reported_content_response(
    storage: ImageStorage, content: ReportedContent
) -> ReportedContentResponse:
    return ReportedContentResponse(
        target_type=content.target_type,
        target_id=content.target_id,
        label=content.label,
        owner_id=content.owner_id,
        owner_name=content.owner_name,
        report_count=content.report_count,
        reasons=[_reason_response(reason, count) for reason, count in content.reasons],
        details=content.details,
        first_reported_at=content.first_reported_at,
        image_url=optional_image_url(storage, content.image),
        public_token=content.public_token,
    )


def _reason_response(reason: ReportReason, count: int) -> ReportReasonCountResponse:
    return ReportReasonCountResponse(reason=reason, count=count)
