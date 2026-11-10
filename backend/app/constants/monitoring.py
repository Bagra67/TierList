SENTRY_REQUEST_BODY_SIZE = "never"
SENTRY_EVENT_REQUEST_KEY = "request"
SENTRY_REQUEST_REMOVED_KEYS: tuple[str, ...] = ("query_string", "cookies")
SENTRY_REQUEST_HEADERS_KEY = "headers"
SENTRY_KEPT_REQUEST_HEADERS: frozenset[str] = frozenset({"user-agent"})
SENTRY_CAPTURED_RESPONSE_STATUS_CODES: frozenset[int] = frozenset()
