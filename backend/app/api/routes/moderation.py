import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.api.dependencies import (
    AccountBanServiceDep,
    AccountReviewServiceDep,
    ImageModerationServiceDep,
    ImageStorageDep,
    ModerationLogServiceDep,
    RecentUploadsServiceDep,
    ReportQueueServiceDep,
    SuperAdminDep,
    TemplateModerationServiceDep,
)
from app.api.presenters.images import recent_upload_response
from app.api.presenters.reports import reported_content_response
from app.api.responses import SUPER_ADMIN_RESPONSES
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.moderation import (
    ACCOUNT_SEARCH_PAGE_SIZE_DEFAULT,
    ACCOUNT_SEARCH_PAGE_SIZE_MAX,
    ACCOUNT_SEARCH_QUERY_MAX_LENGTH,
    MODERATION_LOG_PAGE_SIZE_DEFAULT,
    MODERATION_LOG_PAGE_SIZE_MAX,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
    RECENT_UPLOADS_AUTHOR_FILTER_MAX_LENGTH,
    RECENT_UPLOADS_PAGE_SIZE_DEFAULT,
    RECENT_UPLOADS_PAGE_SIZE_MAX,
    REPORT_QUEUE_PAGE_SIZE_DEFAULT,
    REPORT_QUEUE_PAGE_SIZE_MAX,
)
from app.core.errors import ErrorResponse
from app.exceptions.auth import UserNotFoundError
from app.exceptions.http import AppHTTPException
from app.exceptions.images import ImageModerationConflictError, ImageNotFoundError
from app.exceptions.moderation import (
    AccountNotBannedError,
    BanEndInPastError,
    CannotBanSuperAdminError,
)
from app.exceptions.reports import ReportsNotOpenError
from app.exceptions.templates import TemplateModerationConflictError, TemplateNotFoundError
from app.models.account_ban import AccountBan
from app.models.image import ImageStatus
from app.schemas.moderation import (
    AccountBanResponse,
    AccountPastBanResponse,
    AccountResponse,
    AccountSearchResponse,
    AccountSummaryResponse,
    BanAccountRequest,
    DismissReportsRequest,
    HiddenImagesResponse,
    ModerationActionResponse,
    ModerationLogResponse,
    ModerationReasonRequest,
    OpenReportCountResponse,
    RecentUploadsResponse,
    ReportQueueResponse,
    SuperAdminResponse,
)
from app.schemas.templates import TemplateSummaryResponse
from app.services.account_review import AccountDetails, AccountSearchPage
from app.services.moderation_log import ModerationLogPage
from app.services.recent_uploads import RecentUploadsPage
from app.services.report_queue import ReportQueuePage

router = APIRouter(prefix="/moderation", tags=["moderation"])

IMAGE_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.IMAGE_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.IMAGE_MODERATION_CONFLICT_DESCRIPTION},
}

TEMPLATE_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.TEMPLATE_MODERATION_CONFLICT_DESCRIPTION},
}

ACCOUNT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.ACCOUNT_NOT_FOUND_DESCRIPTION},
}


def _account_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.ACCOUNT_NOT_FOUND,
        detail=messages.ACCOUNT_NOT_FOUND,
    )


BAN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **ACCOUNT_RESPONSES,
    409: {"model": ErrorResponse, "description": messages.CANNOT_BAN_SUPER_ADMIN_DESCRIPTION},
    422: {"model": ErrorResponse, "description": messages.BAN_END_IN_PAST_DESCRIPTION},
}

LIFT_BAN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **ACCOUNT_RESPONSES,
    409: {"model": ErrorResponse, "description": messages.ACCOUNT_NOT_BANNED_DESCRIPTION},
}


def _ban_response(ban: AccountBan | None) -> AccountBanResponse | None:
    return AccountBanResponse.model_validate(ban) if ban is not None else None


def _template_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.TEMPLATE_NOT_FOUND,
        detail=messages.TEMPLATE_NOT_FOUND,
    )


def _template_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_MODERATION_CONFLICT,
        detail=messages.TEMPLATE_MODERATION_CONFLICT,
    )


def _image_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.IMAGE_NOT_FOUND,
        detail=messages.IMAGE_NOT_FOUND,
    )


def _image_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.IMAGE_MODERATION_CONFLICT,
        detail=messages.IMAGE_MODERATION_CONFLICT,
    )


@router.get("/reports", responses=SUPER_ADMIN_RESPONSES)
def list_reports(
    super_admin: SuperAdminDep,
    service: ReportQueueServiceDep,
    storage: ImageStorageDep,
    limit: Annotated[
        int, Query(ge=1, le=REPORT_QUEUE_PAGE_SIZE_MAX)
    ] = REPORT_QUEUE_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
    owner_id: uuid.UUID | None = None,
) -> ReportQueueResponse:
    page: ReportQueuePage = service.page(limit, offset, owner_id)
    return ReportQueueResponse(
        contents=[reported_content_response(storage, content) for content in page.contents],
        has_more=page.has_more,
    )


@router.get("/reports/count", responses=SUPER_ADMIN_RESPONSES)
def count_reports(
    super_admin: SuperAdminDep, service: ReportQueueServiceDep
) -> OpenReportCountResponse:
    return OpenReportCountResponse(open_contents=service.count_open_contents())


@router.post(
    "/reports/dismiss",
    status_code=204,
    responses={
        **SUPER_ADMIN_RESPONSES,
        404: {"model": ErrorResponse, "description": messages.REPORTS_NOT_OPEN_DESCRIPTION},
    },
)
def dismiss_reports(
    body: DismissReportsRequest, super_admin: SuperAdminDep, service: ReportQueueServiceDep
) -> None:
    try:
        service.dismiss(super_admin, body.target_type, body.target_id, body.reason)
    except ReportsNotOpenError as exc:
        raise AppHTTPException(
            status_code=404, code=ErrorCode.REPORTS_NOT_OPEN, detail=messages.REPORTS_NOT_OPEN
        ) from exc


@router.get("/log", responses=SUPER_ADMIN_RESPONSES)
def get_moderation_log(
    super_admin: SuperAdminDep,
    service: ModerationLogServiceDep,
    limit: Annotated[
        int, Query(ge=1, le=MODERATION_LOG_PAGE_SIZE_MAX)
    ] = MODERATION_LOG_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
    actor_id: uuid.UUID | None = None,
    target: Annotated[str | None, Query(max_length=MODERATION_TARGET_LABEL_MAX_LENGTH)] = None,
    account_id: uuid.UUID | None = None,
) -> ModerationLogResponse:
    page: ModerationLogPage = service.page(limit, offset, actor_id, target, account_id)
    return ModerationLogResponse(
        entries=[ModerationActionResponse.model_validate(entry) for entry in page.entries],
        has_more=page.has_more,
    )


@router.get("/super-admins", responses=SUPER_ADMIN_RESPONSES)
def list_super_admins(
    super_admin: SuperAdminDep, service: ModerationLogServiceDep
) -> list[SuperAdminResponse]:
    return [SuperAdminResponse.model_validate(user) for user in service.super_admins()]


@router.post("/images/{image_id}/hide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def hide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    try:
        service.hide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.post("/images/{image_id}/unhide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def unhide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    try:
        service.unhide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.post("/images/{image_id}/delete", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def delete_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    try:
        service.delete(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise _image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.get("/images", responses=SUPER_ADMIN_RESPONSES)
def list_recent_uploads(
    super_admin: SuperAdminDep,
    service: RecentUploadsServiceDep,
    storage: ImageStorageDep,
    limit: Annotated[
        int, Query(ge=1, le=RECENT_UPLOADS_PAGE_SIZE_MAX)
    ] = RECENT_UPLOADS_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
    author: Annotated[str | None, Query(max_length=RECENT_UPLOADS_AUTHOR_FILTER_MAX_LENGTH)] = None,
    created_after: AwareDatetime | None = None,
    created_before: AwareDatetime | None = None,
    status: Literal["visible", "hidden"] | None = None,
    owner_id: uuid.UUID | None = None,
) -> RecentUploadsResponse:
    page: RecentUploadsPage = service.page(
        limit,
        offset,
        author,
        created_after,
        created_before,
        ImageStatus(status) if status is not None else None,
        owner_id,
    )
    return RecentUploadsResponse(
        images=[recent_upload_response(storage, upload) for upload in page.uploads],
        has_more=page.has_more,
    )


@router.post(
    "/templates/{template_id}/hide", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def hide_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    try:
        service.hide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


@router.post(
    "/templates/{template_id}/unhide", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def unhide_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    try:
        service.unhide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


@router.post(
    "/templates/{template_id}/delete", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def delete_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    try:
        service.delete(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise _template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


@router.get("/accounts", responses=SUPER_ADMIN_RESPONSES)
def search_accounts(
    super_admin: SuperAdminDep,
    service: AccountReviewServiceDep,
    bans: AccountBanServiceDep,
    query: Annotated[str | None, Query(max_length=ACCOUNT_SEARCH_QUERY_MAX_LENGTH)] = None,
    limit: Annotated[
        int, Query(ge=1, le=ACCOUNT_SEARCH_PAGE_SIZE_MAX)
    ] = ACCOUNT_SEARCH_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccountSearchResponse:
    page: AccountSearchPage = service.search(query, limit, offset)
    banned: set[uuid.UUID] = bans.banned_user_ids([user.id for user in page.accounts])
    return AccountSearchResponse(
        accounts=[
            AccountSummaryResponse(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                created_at=user.created_at,
                role=user.role,
                banned=user.id in banned,
            )
            for user in page.accounts
        ],
        has_more=page.has_more,
    )


@router.get("/accounts/{user_id}", responses=ACCOUNT_RESPONSES)
def get_account(
    user_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: AccountReviewServiceDep,
    bans: AccountBanServiceDep,
) -> AccountResponse:
    try:
        details: AccountDetails = service.details(user_id)
    except UserNotFoundError as exc:
        raise _account_not_found() from exc
    return AccountResponse(
        id=details.user.id,
        display_name=details.user.display_name,
        email=details.user.email,
        created_at=details.user.created_at,
        email_verified=details.user.email_verified,
        role=details.user.role,
        ban=_ban_response(bans.active_ban(details.user.id)),
        past_bans=[
            AccountPastBanResponse.model_validate(past_ban)
            for past_ban in bans.past_bans(details.user.id)
        ],
        templates=[
            TemplateSummaryResponse.model_validate(summary) for summary in details.templates
        ],
    )


@router.post("/accounts/{user_id}/hide-images", responses=ACCOUNT_RESPONSES)
def hide_account_images(
    user_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: AccountReviewServiceDep,
) -> HiddenImagesResponse:
    try:
        hidden_count: int = service.hide_all_images(super_admin, user_id, body.reason)
    except UserNotFoundError as exc:
        raise _account_not_found() from exc
    return HiddenImagesResponse(hidden_count=hidden_count)


@router.post("/accounts/{user_id}/ban", status_code=204, responses=BAN_RESPONSES)
def ban_account(
    user_id: uuid.UUID,
    body: BanAccountRequest,
    super_admin: SuperAdminDep,
    service: AccountBanServiceDep,
) -> None:
    try:
        service.ban(super_admin, user_id, body.reason, body.ends_at)
    except UserNotFoundError as exc:
        raise _account_not_found() from exc
    except CannotBanSuperAdminError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.CANNOT_BAN_SUPER_ADMIN,
            detail=messages.CANNOT_BAN_SUPER_ADMIN,
        ) from exc
    except BanEndInPastError as exc:
        raise AppHTTPException(
            status_code=422,
            code=ErrorCode.BAN_END_IN_PAST,
            detail=messages.BAN_END_IN_PAST,
        ) from exc


@router.post("/accounts/{user_id}/lift-ban", status_code=204, responses=LIFT_BAN_RESPONSES)
def lift_account_ban(
    user_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: AccountBanServiceDep,
) -> None:
    try:
        service.lift(super_admin, user_id, body.reason)
    except UserNotFoundError as exc:
        raise _account_not_found() from exc
    except AccountNotBannedError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.ACCOUNT_NOT_BANNED,
            detail=messages.ACCOUNT_NOT_BANNED,
        ) from exc
