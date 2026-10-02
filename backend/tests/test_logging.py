import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.core.logging import LoggingSettings, configure_logging
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
def no_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    # Dossier sans .env : seules les variables d'environnement du test comptent.
    monkeypatch.chdir(tmp_path)
    return monkeypatch


@pytest.fixture(autouse=True)
def restore_default_logging() -> Iterator[None]:
    yield
    configure_logging("INFO")
    app.dependency_overrides.clear()


def test_log_level_defaults_to_info(no_env_file: pytest.MonkeyPatch):
    no_env_file.delenv("LOG_LEVEL", raising=False)
    assert LoggingSettings().log_level == "INFO"


def test_log_level_is_case_insensitive(no_env_file: pytest.MonkeyPatch):
    no_env_file.setenv("LOG_LEVEL", "debug")
    assert LoggingSettings().log_level == "DEBUG"


def test_invalid_log_level_is_rejected(no_env_file: pytest.MonkeyPatch):
    no_env_file.setenv("LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        LoggingSettings()


def test_app_logs_use_uvicorn_format_and_respect_level(capsys: pytest.CaptureFixture[str]):
    configure_logging("WARNING")
    logger = logging.getLogger("app.example")

    logger.info("hidden message")
    logger.warning("visible message")

    stderr = capsys.readouterr().err
    assert "hidden message" not in stderr
    assert "WARNING:" in stderr
    assert "app.example - visible message" in stderr


class UnreachableDatabaseSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_database_failure_is_logged_with_traceback(capsys: pytest.CaptureFixture[str]):
    configure_logging("INFO")
    app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response = TestClient(app).get("/health/db")

    assert response.status_code == 503
    stderr = capsys.readouterr().err
    assert "ERROR:" in stderr
    assert "app.main - Échec de la connexion à la base de données" in stderr
    assert "OperationalError" in stderr
