import re

SENTRY_REQUEST_BODY_SIZE = "never"
SENTRY_EVENT_REQUEST_KEY = "request"
SENTRY_REQUEST_REMOVED_KEYS: tuple[str, ...] = ("query_string", "cookies")
SENTRY_REQUEST_HEADERS_KEY = "headers"
SENTRY_REQUEST_URL_KEY = "url"
SENTRY_KEPT_REQUEST_HEADERS: frozenset[str] = frozenset({"user-agent"})
SENTRY_CAPTURED_RESPONSE_STATUS_CODES: frozenset[int] = frozenset()

SENTRY_FILTERED = "[Filtered]"
SENTRY_SECRET_PATH_SEGMENT: re.Pattern[str] = re.compile(r"(/(?:results|rooms|r)/)[^/?#\s\"']+")
SENTRY_URL_QUERY_OR_FRAGMENT: re.Pattern[str] = re.compile(r"[?#].*", re.DOTALL)
SENTRY_URL_DATA_KEYS: tuple[str, ...] = ("url", "aws.request.url")
SENTRY_REMOVED_URL_DATA_KEYS: tuple[str, ...] = ("http.query", "http.fragment")
SENTRY_IGNORED_LOGGERS: tuple[str, ...] = ("uvicorn.access",)
