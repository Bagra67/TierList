import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Breadcrumb, BreadcrumbHint, Event, Hint

from app.constants.monitoring import (
    SENTRY_CAPTURED_RESPONSE_STATUS_CODES,
    SENTRY_EMAIL_ADDRESS,
    SENTRY_EVENT_REQUEST_KEY,
    SENTRY_FILTERED,
    SENTRY_HTTP_SPAN_OP_PREFIX,
    SENTRY_IGNORED_LOGGERS,
    SENTRY_KEPT_REQUEST_HEADERS,
    SENTRY_REMOVED_URL_DATA_KEYS,
    SENTRY_REQUEST_BODY_SIZE,
    SENTRY_REQUEST_HEADERS_KEY,
    SENTRY_REQUEST_REMOVED_KEYS,
    SENTRY_REQUEST_URL_KEY,
    SENTRY_SECRET_LINK_PARAM,
    SENTRY_SECRET_PATH_SEGMENT,
    SENTRY_URL_DATA_KEYS,
    SENTRY_URL_QUERY_OR_FRAGMENT,
)
from app.core.config import Settings


def mask_secret_paths(text: str) -> str:
    return SENTRY_SECRET_PATH_SEGMENT.sub(rf"\g<1>{SENTRY_FILTERED}", text)


def scrub_url(url: str) -> str:
    return mask_secret_paths(SENTRY_URL_QUERY_OR_FRAGMENT.sub("", url))


def mask_secrets_in_text(text: str) -> str:
    without_emails: str = SENTRY_EMAIL_ADDRESS.sub(SENTRY_FILTERED, text)
    without_link_secrets: str = SENTRY_SECRET_LINK_PARAM.sub(
        rf"\g<1>{SENTRY_FILTERED}", without_emails
    )
    return mask_secret_paths(without_link_secrets)


def _mask_if_text(value: object) -> object:
    return mask_secrets_in_text(value) if isinstance(value, str) else value


def _scrub_url_data(data: dict[str, Any]) -> None:
    for key in SENTRY_REMOVED_URL_DATA_KEYS:
        data.pop(key, None)
    for key in SENTRY_URL_DATA_KEYS:
        url: object = data.get(key)
        if isinstance(url, str):
            data[key] = scrub_url(url)


def _scrub_request(event: Event) -> None:
    request: dict[str, Any] | None = event.get(SENTRY_EVENT_REQUEST_KEY)
    if request is None:
        return
    for key in SENTRY_REQUEST_REMOVED_KEYS:
        request.pop(key, None)
    headers: dict[str, str] = request.get(SENTRY_REQUEST_HEADERS_KEY) or {}
    request[SENTRY_REQUEST_HEADERS_KEY] = {
        name: value
        for name, value in headers.items()
        if name.lower() in SENTRY_KEPT_REQUEST_HEADERS
    }
    url: object = request.get(SENTRY_REQUEST_URL_KEY)
    if isinstance(url, str):
        request[SENTRY_REQUEST_URL_KEY] = scrub_url(url)


def _scrub_log_entry(event: Event) -> None:
    log_entry: object = event.get("logentry")
    if not isinstance(log_entry, dict):
        return
    for key in ("message", "formatted"):
        if key in log_entry:
            log_entry[key] = _mask_if_text(log_entry[key])
    params: object = log_entry.get("params")
    if isinstance(params, list | tuple):
        log_entry["params"] = [_mask_if_text(param) for param in params]


def _scrub_exception_messages(event: Event) -> None:
    exceptions: list[dict[str, Any]] = (event.get("exception") or {}).get("values") or []
    for exception in exceptions:
        if "value" in exception:
            exception["value"] = _mask_if_text(exception["value"])


def scrub_event(event: Event, _hint: Hint) -> Event:
    _scrub_request(event)
    _scrub_log_entry(event)
    _scrub_exception_messages(event)
    transaction: object = event.get("transaction")
    if isinstance(transaction, str):
        event["transaction"] = mask_secret_paths(transaction)
    return event


def scrub_transaction(event: Event, hint: Hint) -> Event:
    scrub_event(event, hint)
    spans: object = event.get("spans")
    if not isinstance(spans, list):
        return event
    for span in spans:
        description: object = span.get("description")
        if isinstance(description, str):
            span["description"] = (
                scrub_url(description)
                if str(span.get("op", "")).startswith(SENTRY_HTTP_SPAN_OP_PREFIX)
                else mask_secrets_in_text(description)
            )
        span_data: object = span.get("data")
        if isinstance(span_data, dict):
            _scrub_url_data(span_data)
    return event


def scrub_breadcrumb(breadcrumb: Breadcrumb, _hint: BreadcrumbHint) -> Breadcrumb:
    message: object = breadcrumb.get("message")
    if isinstance(message, str):
        breadcrumb["message"] = mask_secrets_in_text(message)
    breadcrumb_data: object = breadcrumb.get("data")
    if isinstance(breadcrumb_data, dict):
        _scrub_url_data(breadcrumb_data)
    return breadcrumb


def configure_sentry(settings: Settings) -> bool:
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.app_release,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        max_request_body_size=SENTRY_REQUEST_BODY_SIZE,
        include_local_variables=False,
        before_send=scrub_event,
        before_send_transaction=scrub_transaction,
        before_breadcrumb=scrub_breadcrumb,
        integrations=[
            LoggingIntegration(event_level=logging.ERROR),
            StarletteIntegration(failed_request_status_codes=SENTRY_CAPTURED_RESPONSE_STATUS_CODES),
            FastApiIntegration(failed_request_status_codes=SENTRY_CAPTURED_RESPONSE_STATUS_CODES),
        ],
    )
    for logger_name in SENTRY_IGNORED_LOGGERS:
        ignore_logger(logger_name)
    return True
