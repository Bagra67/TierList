import re

from app.constants.auth import TOKEN_PARAM
from app.constants.rooms import GUEST_LINK_FRAGMENT

SENTRY_REQUEST_BODY_SIZE = "never"
SENTRY_EVENT_REQUEST_KEY = "request"
SENTRY_REQUEST_REMOVED_KEYS: tuple[str, ...] = ("query_string", "cookies")
SENTRY_REQUEST_HEADERS_KEY = "headers"
SENTRY_REQUEST_URL_KEY = "url"
SENTRY_KEPT_REQUEST_HEADERS: frozenset[str] = frozenset({"user-agent"})
SENTRY_CAPTURED_RESPONSE_STATUS_CODES: frozenset[int] = frozenset()

SENTRY_FILTERED = "[Filtered]"
SENTRY_SECRET_PATH_SEGMENT: re.Pattern[str] = re.compile(
    r"(/(?:results|rooms|r)/)[^/?#\s\"']+", re.IGNORECASE
)
SENTRY_SECRET_LINK_PARAM: re.Pattern[str] = re.compile(
    rf"([?&#](?:{TOKEN_PARAM}|{GUEST_LINK_FRAGMENT})=)[^&#\s\"']+", re.IGNORECASE
)
SENTRY_EMAIL_ADDRESS: re.Pattern[str] = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
SENTRY_URL_QUERY_OR_FRAGMENT: re.Pattern[str] = re.compile(r"[?#].*", re.DOTALL)
SENTRY_URL_DATA_KEYS: tuple[str, ...] = ("url", "aws.request.url")
SENTRY_REMOVED_URL_DATA_KEYS: tuple[str, ...] = ("http.query", "http.fragment")
SENTRY_IGNORED_LOGGERS: tuple[str, ...] = ("uvicorn.access",)
SENTRY_HTTP_SPAN_OP_PREFIX = "http"
