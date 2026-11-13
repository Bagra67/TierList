import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.api.dependencies import (
    AccountBanServiceDep,
    AccountReviewServiceDep,
    GameServiceDep,
    ImageModerationServiceDep,
    ImageStorageDep,
    ModerationLogServiceDep,
    RecentUploadsServiceDep,
    ReportQueueServiceDep,
    SuperAdminDep,
    TemplateModerationServiceDep,
)
from app.api.errors import image_not_found, template_not_found
from app.api.presenters.images import recent_upload_response
from app.api.presenters.reports import reported_content_response
from app.api.presenters.templates import reviewed_template_response
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
    ImagesHidingInProgressError,
)
from app.exceptions.reports import (
    GameModerationConflictError,
    GameNotFoundError,
    NicknameNotFoundError,
    ReportsNotOpenError,
)
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
    HiddenGameResponse,
    HiddenGamesResponse,
    HiddenImagesResponse,
    ModerationActionResponse,
    ModerationLogResponse,
    ModerationReasonRequest,
    OpenReportCountResponse,
    RecentUploadsResponse,
    RemoveNicknameRequest,
    ReportQueueResponse,
    ReviewedTemplateResponse,
    SuperAdminResponse,
)
from app.schemas.templates import TemplateSummaryResponse
from app.services.account_review import AccountDetails, AccountSearchPage, HiddenImagesBatch
from app.services.moderation_log import ModerationLogPage
from app.services.recent_uploads import RecentUploadsPage
from app.services.report_queue import HiddenGamesPage, ReportQueuePage
from app.services.template_moderation import ReviewedTemplate

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


def _template_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.TEMPLATE_MODERATION_CONFLICT,
        detail=messages.TEMPLATE_MODERATION_CONFLICT,
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
    """Queue of open reports, grouped by content: the most reported first, then the oldest. Never
    the author of a report. Paginated by `limit` and `offset`; `owner_id` keeps the contents of one
    account."""
    page: ReportQueuePage = service.page(limit, offset, owner_id)
    return ReportQueueResponse(
        contents=[reported_content_response(storage, content) for content in page.contents],
        has_more=page.has_more,
    )


@router.get("/reports/count", responses=SUPER_ADMIN_RESPONSES)
def count_reports(
    super_admin: SuperAdminDep, service: ReportQueueServiceDep
) -> OpenReportCountResponse:
    """Number of reported contents waiting for a decision (contents, not reports), for the
    moderation menu."""
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
    """Dismisses the open reports of a content: the content does not change. Written to the
    moderation log with the reason."""
    try:
        service.dismiss(super_admin, body.target_type, body.target_id, body.reason)
    except ReportsNotOpenError as exc:
        raise AppHTTPException(
            status_code=404, code=ErrorCode.REPORTS_NOT_OPEN, detail=messages.REPORTS_NOT_OPEN
        ) from exc


@router.post(
    "/nicknames/remove",
    status_code=204,
    responses={
        **SUPER_ADMIN_RESPONSES,
        404: {"model": ErrorResponse, "description": messages.NICKNAME_NOT_FOUND_DESCRIPTION},
    },
)
def remove_nickname(
    body: RemoveNicknameRequest, super_admin: SuperAdminDep, service: ReportQueueServiceDep
) -> None:
    """Replaces a reported nickname with a neutral code, in rooms and results. Cannot be undone: the
    old nickname only stays in the log."""
    try:
        service.remove_nickname(super_admin, body.target_id, body.reason)
    except NicknameNotFoundError as exc:
        raise AppHTTPException(
            status_code=404, code=ErrorCode.NICKNAME_NOT_FOUND, detail=messages.NICKNAME_NOT_FOUND
        ) from exc


@router.get("/games/hidden", responses=SUPER_ADMIN_RESPONSES)
def list_hidden_games(
    super_admin: SuperAdminDep,
    service: ReportQueueServiceDep,
    limit: Annotated[
        int, Query(ge=1, le=REPORT_QUEUE_PAGE_SIZE_MAX)
    ] = REPORT_QUEUE_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HiddenGamesResponse:
    """The games hidden by moderation, so they can be made visible again. Paginated by `limit` and
    `offset`."""
    page: HiddenGamesPage = service.hidden_games(limit, offset)
    return HiddenGamesResponse(
        games=[
            HiddenGameResponse(id=game.id, template_name=game.snapshot.name, hidden_at=hidden_at)
            for game in page.games
            if (hidden_at := game.hidden_at) is not None
        ],
        has_more=page.has_more,
    )


def _game_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404, code=ErrorCode.GAME_NOT_FOUND, detail=messages.GAME_NOT_FOUND
    )


def _game_moderation_conflict() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.GAME_MODERATION_CONFLICT,
        detail=messages.GAME_MODERATION_CONFLICT,
    )


GAME_MODERATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPER_ADMIN_RESPONSES,
    404: {"model": ErrorResponse, "description": messages.GAME_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.GAME_MODERATION_CONFLICT_DESCRIPTION},
}


@router.post("/games/{game_id}/hide", status_code=204, responses=GAME_MODERATION_RESPONSES)
def hide_game(
    game_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ReportQueueServiceDep,
) -> None:
    """Hides a closed game: its results link answers like an unknown link."""
    try:
        service.hide_game(super_admin, game_id, body.reason)
    except GameNotFoundError as exc:
        raise _game_not_found() from exc
    except GameModerationConflictError as exc:
        raise _game_moderation_conflict() from exc


@router.post("/games/{game_id}/unhide", status_code=204, responses=GAME_MODERATION_RESPONSES)
def unhide_game(
    game_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ReportQueueServiceDep,
) -> None:
    """Makes a hidden game visible: its results link works again. Written to the log with the
    reason."""
    try:
        service.unhide_game(super_admin, game_id, body.reason)
    except GameNotFoundError as exc:
        raise _game_not_found() from exc
    except GameModerationConflictError as exc:
        raise _game_moderation_conflict() from exc


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
    """The moderation log, most recent first. Filters: `actor_id` (a super admin), `target` (text
    searched in the target's name, case-insensitive), `account_id` (the decisions about an account,
    its templates and its images). Paginated by `limit` and `offset`."""
    page: ModerationLogPage = service.page(limit, offset, actor_id, target, account_id)
    return ModerationLogResponse(
        entries=[ModerationActionResponse.model_validate(entry) for entry in page.entries],
        has_more=page.has_more,
    )


@router.get("/super-admins", responses=SUPER_ADMIN_RESPONSES)
def list_super_admins(
    super_admin: SuperAdminDep, service: ModerationLogServiceDep
) -> list[SuperAdminResponse]:
    """The super admins, by name: the choices of the log's "Super admin" filter."""
    return [SuperAdminResponse.model_validate(user) for user in service.super_admins()]


@router.post("/images/{image_id}/hide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def hide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    """Hides a visible image: it is no longer served at its public address and shows as "removed"
    everywhere. Written to the log with the reason."""
    try:
        service.hide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.post("/images/{image_id}/unhide", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def unhide_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    """Makes a hidden image visible. Written to the log with the reason."""
    try:
        service.unhide(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise image_not_found() from exc
    except ImageModerationConflictError as exc:
        raise _image_moderation_conflict() from exc


@router.post("/images/{image_id}/delete", status_code=204, responses=IMAGE_MODERATION_RESPONSES)
def delete_image(
    image_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: ImageModerationServiceDep,
) -> None:
    """Deletes an image, visible or hidden: its file is erased and it shows as "removed" everywhere.
    Written to the log with the reason."""
    try:
        service.delete(super_admin, image_id, body.reason)
    except ImageNotFoundError as exc:
        raise image_not_found() from exc
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
    """The latest uploaded images, most recent first, with their author and their use (templates,
    games). Filters: `author` (name or email, case-insensitive), `created_after` and
    `created_before`, `status`, `owner_id`. Paginated by `limit` and `offset`."""
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


@router.get(
    "/templates/{template_id}",
    responses={
        **SUPER_ADMIN_RESPONSES,
        404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
    },
)
def get_template_for_review(
    template_id: uuid.UUID,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
    storage: ImageStorageDep,
) -> ReviewedTemplateResponse:
    """Reads the content of a non-deleted template, even a private one (US-1.8). Read-only."""
    try:
        reviewed: ReviewedTemplate = service.review(template_id)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    return reviewed_template_response(reviewed, storage)


@router.post(
    "/templates/{template_id}/hide", status_code=204, responses=TEMPLATE_MODERATION_RESPONSES
)
def hide_template(
    template_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: TemplateModerationServiceDep,
) -> None:
    """Hides a template that is neither hidden nor deleted, public or private: it can no longer be
    used for a new game, and its owner sees the reason. Written to the log."""
    try:
        service.hide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
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
    """Lifts the hiding of a template that is not deleted; its public or private visibility does not
    change, and the reason is cleared from the template. Written to the log with the reason."""
    try:
        service.unhide(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
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
    """Deletes a template, visible or hidden, like a deletion by its owner; the owner sees the
    reason until the purge. Written to the log."""
    try:
        service.delete(super_admin, template_id, body.reason)
    except TemplateNotFoundError as exc:
        raise template_not_found() from exc
    except TemplateModerationConflictError as exc:
        raise _template_moderation_conflict() from exc


@router.get("/accounts", responses=SUPER_ADMIN_RESPONSES)
def search_accounts(
    super_admin: SuperAdminDep,
    service: AccountReviewServiceDep,
    query: Annotated[str | None, Query(max_length=ACCOUNT_SEARCH_QUERY_MAX_LENGTH)] = None,
    limit: Annotated[
        int, Query(ge=1, le=ACCOUNT_SEARCH_PAGE_SIZE_MAX)
    ] = ACCOUNT_SEARCH_PAGE_SIZE_DEFAULT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccountSearchResponse:
    """Searches accounts by name or email, sorted by name. Paginated by `limit` and `offset`;
    `has_more` tells whether accounts are left."""
    page: AccountSearchPage = service.search(query, limit, offset)
    return AccountSearchResponse(
        accounts=[
            AccountSummaryResponse(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                created_at=user.created_at,
                role=user.role,
                banned=user.id in page.banned_ids,
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
) -> AccountResponse:
    """The page of an account: its details, its active ban, its past bans and its templates."""
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
        ban=_ban_response(details.active_ban),
        past_bans=[
            AccountPastBanResponse.model_validate(past_ban) for past_ban in details.past_bans
        ],
        templates=[
            TemplateSummaryResponse.model_validate(summary) for summary in details.templates
        ],
    )


HIDE_IMAGES_RESPONSES: dict[int | str, dict[str, Any]] = {
    **ACCOUNT_RESPONSES,
    409: {"model": ErrorResponse, "description": messages.IMAGES_HIDING_IN_PROGRESS_DESCRIPTION},
}


@router.post("/accounts/{user_id}/hide-images", responses=HIDE_IMAGES_RESPONSES)
def hide_account_images(
    user_id: uuid.UUID,
    body: ModerationReasonRequest,
    super_admin: SuperAdminDep,
    service: AccountReviewServiceDep,
) -> HiddenImagesResponse:
    """Hides the visible images of an account, in batches. Send the request again while `has_more`
    is true."""
    try:
        batch: HiddenImagesBatch = service.hide_all_images(super_admin, user_id, body.reason)
    except UserNotFoundError as exc:
        raise _account_not_found() from exc
    except ImagesHidingInProgressError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.IMAGES_HIDING_IN_PROGRESS,
            detail=messages.IMAGES_HIDING_IN_PROGRESS,
        ) from exc
    return HiddenImagesResponse(hidden_count=batch.hidden_count, has_more=batch.has_more)


@router.post("/accounts/{user_id}/ban", status_code=204, responses=BAN_RESPONSES)
def ban_account(
    user_id: uuid.UUID,
    body: BanAccountRequest,
    super_admin: SuperAdminDep,
    service: AccountBanServiceDep,
    games: GameServiceDep,
) -> None:
    """Bans an account, until `ends_at` or permanently (`ends_at` null); an active ban is lifted
    first. The account is signed out everywhere and can no longer sign in; its contents stay online.
    Written to the log."""
    try:
        service.ban(
            super_admin,
            user_id,
            body.reason,
            body.ends_at,
            after_ban=games.disconnect_banned_account,
        )
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
    """Lifts the active ban of an account: it can sign in again; its sessions stay closed. Written
    to the log with the reason."""
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
