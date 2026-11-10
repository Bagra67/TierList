import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

from app.constants.monitoring import (
    SENTRY_CAPTURED_RESPONSE_STATUS_CODES,
    SENTRY_EVENT_REQUEST_KEY,
    SENTRY_KEPT_REQUEST_HEADERS,
    SENTRY_REQUEST_BODY_SIZE,
    SENTRY_REQUEST_HEADERS_KEY,
    SENTRY_REQUEST_REMOVED_KEYS,
)
from app.core.config import Settings


def remove_request_personal_data(event: Event, _hint: Hint) -> Event:
    request: dict[str, Any] | None = event.get(SENTRY_EVENT_REQUEST_KEY)
    if request is None:
        return event
    for key in SENTRY_REQUEST_REMOVED_KEYS:
        request.pop(key, None)
    headers: dict[str, str] = request.get(SENTRY_REQUEST_HEADERS_KEY) or {}
    request[SENTRY_REQUEST_HEADERS_KEY] = {
        name: value
        for name, value in headers.items()
        if name.lower() in SENTRY_KEPT_REQUEST_HEADERS
    }
    return event


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
        before_send=remove_request_personal_data,
        before_send_transaction=remove_request_personal_data,
        integrations=[
            LoggingIntegration(event_level=logging.ERROR),
            StarletteIntegration(failed_request_status_codes=SENTRY_CAPTURED_RESPONSE_STATUS_CODES),
            FastApiIntegration(failed_request_status_codes=SENTRY_CAPTURED_RESPONSE_STATUS_CODES),
        ],
    )
    return True
