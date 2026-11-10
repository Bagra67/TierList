from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Response

from app.api.dependencies import OptionalUserDep, ReportServiceDep, SettingsDep
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.reports import REPORT_COOKIE, REPORT_COOKIE_MAX_AGE_SECONDS
from app.core.config import Settings
from app.core.errors import ErrorResponse
from app.core.security import generate_guest_token
from app.exceptions.http import AppHTTPException
from app.exceptions.reports import (
    ReportAlreadyOpenError,
    ReportDetailsRequiredError,
    ReportLimitReachedError,
    ReportTargetNotFoundError,
)
from app.models.report import Report
from app.schemas.reports import CreateReportRequest, ReportResponse
from app.services.reports import Reporter, ReportRequest, reporter_of

router = APIRouter(prefix="/reports", tags=["reports"])

CREATE_REPORT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.REPORT_TARGET_NOT_FOUND_DESCRIPTION},
    409: {"model": ErrorResponse, "description": messages.REPORT_ALREADY_OPEN_DESCRIPTION},
    422: {"model": ErrorResponse, "description": messages.REPORT_DETAILS_REQUIRED_DESCRIPTION},
    429: {"model": ErrorResponse, "description": messages.REPORT_LIMIT_REACHED_DESCRIPTION},
}


def _set_report_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REPORT_COOKIE,
        token,
        max_age=REPORT_COOKIE_MAX_AGE_SECONDS,
        path=settings.report_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )


@router.post("", status_code=201, responses=CREATE_REPORT_RESPONSES)
def create_report(
    payload: CreateReportRequest,
    response: Response,
    user: OptionalUserDep,
    service: ReportServiceDep,
    settings: SettingsDep,
    report_token: Annotated[str | None, Cookie(alias=REPORT_COOKIE)] = None,
) -> ReportResponse:
    """Signale un contenu, avec un compte ou sans : un cookie reconnaît alors le navigateur."""
    browser_token: str = report_token or generate_guest_token()
    reporter: Reporter = reporter_of(user.id if user is not None else None, browser_token)
    try:
        report: Report = service.report(
            reporter,
            ReportRequest(payload.target_kind, payload.target_id, payload.reason, payload.details),
        )
    except ReportTargetNotFoundError as exc:
        raise AppHTTPException(
            status_code=404,
            code=ErrorCode.REPORT_TARGET_NOT_FOUND,
            detail=messages.REPORT_TARGET_NOT_FOUND,
        ) from exc
    except ReportAlreadyOpenError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.REPORT_ALREADY_OPEN,
            detail=messages.REPORT_ALREADY_OPEN,
        ) from exc
    except ReportDetailsRequiredError as exc:
        raise AppHTTPException(
            status_code=422,
            code=ErrorCode.REPORT_DETAILS_REQUIRED,
            detail=messages.REPORT_DETAILS_REQUIRED,
        ) from exc
    except ReportLimitReachedError as exc:
        raise AppHTTPException(
            status_code=429,
            code=ErrorCode.REPORT_LIMIT_REACHED,
            detail=messages.REPORT_LIMIT_REACHED.format(max_reports=exc.max_reports),
            params={"max_reports": exc.max_reports},
        ) from exc
    if user is None and not report_token:
        _set_report_cookie(response, browser_token, settings)
    return ReportResponse(id=report.id)
