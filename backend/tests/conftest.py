import logging
import os
import sys

import pytest

from app.constants.logging import APP_LOG_HANDLER, APP_LOGGER

os.environ["SENTRY_DSN"] = ""


@pytest.fixture(autouse=True)
def rebind_app_logs_to_stderr_captured_under_xdist() -> None:
    app_logger: logging.Logger = logging.getLogger(APP_LOGGER)
    for handler in app_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.name == APP_LOG_HANDLER:
            handler.stream = sys.stderr
