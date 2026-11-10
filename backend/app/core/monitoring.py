import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event, Hint

from app.constants.monitoring import (
    SENTRY_EVENT_QUERY_STRING_KEY,
    SENTRY_EVENT_REQUEST_KEY,
    SENTRY_REQUEST_BODY_SIZE,
)
from app.core.config import Settings


def remove_query_string(event: Event, _hint: Hint) -> Event:
    request: dict[str, Any] | None = event.get(SENTRY_EVENT_REQUEST_KEY)
    if request is not None:
        request.pop(SENTRY_EVENT_QUERY_STRING_KEY, None)
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
        before_send=remove_query_string,
        integrations=[LoggingIntegration(event_level=logging.ERROR)],
    )
    return True
