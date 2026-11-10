import logging
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from httpx2 import Response
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport
from sentry_sdk.types import Event

import app.core.monitoring as monitoring_module
from app.core.config import Settings, get_settings
from app.core.monitoring import configure_sentry, remove_query_string
from app.main import api_app, app

FAKE_DSN: str = "https://public-key@sentry.example.invalid/1"

REQUIRED_SETTINGS: dict[str, object] = {
    "postgres_user": "tierlist",
    "postgres_password": "unit-test-password",
    "postgres_db": "tierlist",
    "jwt_secret_key": "unit-test-secret-key-of-at-least-32-chars",
}


class CapturingTransport(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[Event] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        event: Event | None = envelope.get_event()
        if event is not None:
            self.events.append(event)


@pytest.fixture(autouse=True)
def isolate_from_local_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENTRY_DSN", raising=False)


@pytest.fixture(autouse=True)
def reset_sentry() -> Iterator[None]:
    yield
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)
    api_app.dependency_overrides.clear()


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> CapturingTransport:
    capturing_transport: CapturingTransport = CapturingTransport()
    init_with_transport: partial[Any] = partial(sentry_sdk.init, transport=capturing_transport)
    monkeypatch.setattr(monitoring_module.sentry_sdk, "init", init_with_transport)
    return capturing_transport


def make_settings(**overrides: object) -> Settings:
    return Settings.model_validate({**REQUIRED_SETTINGS, **overrides})


def test_sentry_settings_default_to_disabled() -> None:
    settings: Settings = make_settings()

    assert settings.sentry_dsn is None
    assert settings.sentry_environment == "local"
    assert settings.sentry_traces_sample_rate == 0


@pytest.mark.parametrize("sample_rate", [-0.1, 1.1])
def test_the_traces_sample_rate_stays_between_zero_and_one(sample_rate: float) -> None:
    with pytest.raises(ValueError, match="sentry_traces_sample_rate"):
        make_settings(sentry_traces_sample_rate=sample_rate)


def test_sentry_is_not_started_without_a_dsn() -> None:
    started: bool = configure_sentry(make_settings())

    assert started is False
    assert sentry_sdk.get_client().is_active() is False


def test_sentry_starts_with_the_release_and_without_personal_data(
    transport: CapturingTransport,
) -> None:
    started: bool = configure_sentry(
        make_settings(sentry_dsn=FAKE_DSN, sentry_environment="staging", app_release="v1.2.3")
    )

    options: dict[str, Any] = sentry_sdk.get_client().options
    assert started is True
    assert options["environment"] == "staging"
    assert options["release"] == "v1.2.3"
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["include_local_variables"] is False


def test_an_error_logged_by_the_app_is_sent_to_sentry(transport: CapturingTransport) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logging.getLogger("app.example").exception("Erreur non gérée")
    sentry_sdk.flush()

    assert len(transport.events) == 1
    event: Event = transport.events[0]
    assert event.get("logentry", {}).get("message") == "Erreur non gérée"
    assert event.get("exception", {})["values"][0]["type"] == "RuntimeError"


def test_a_warning_is_not_sent_to_sentry(transport: CapturingTransport) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))

    logging.getLogger("app.example").warning("Avertissement")
    sentry_sdk.flush()

    assert transport.events == []


def test_the_query_string_is_removed_from_the_event() -> None:
    event: Event = {
        "request": {"url": "https://tierlist.test/api/x", "query_string": "code=s3cr3t"}
    }

    cleaned: Event = remove_query_string(event, {})

    assert cleaned.get("request") == {"url": "https://tierlist.test/api/x"}


def test_an_event_without_request_is_left_unchanged() -> None:
    event: Event = {"message": "nightly purge failed"}

    assert remove_query_string(event, {}) == {"message": "nightly purge failed"}


def test_client_config_without_sentry_sends_a_null_dsn() -> None:
    api_app.dependency_overrides[get_settings] = lambda: make_settings(app_release="v1.2.3")

    response: Response = TestClient(app).get("/api/client-config")

    assert response.status_code == 200
    assert response.json() == {"sentry_dsn": None, "environment": "local", "release": "v1.2.3"}


def test_client_config_sends_the_sentry_settings() -> None:
    api_app.dependency_overrides[get_settings] = lambda: make_settings(
        sentry_dsn=FAKE_DSN, sentry_environment="production", app_release="v2.0.0"
    )

    response: Response = TestClient(app).get("/api/client-config")

    assert response.json() == {
        "sentry_dsn": FAKE_DSN,
        "environment": "production",
        "release": "v2.0.0",
    }
