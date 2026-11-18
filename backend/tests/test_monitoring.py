import logging
import time
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
from app.api.dependencies import get_game_results_service
from app.core.config import Settings, get_settings
from app.core.monitoring import (
    configure_sentry,
    mask_secret_paths,
    mask_secrets_in_text,
    scrub_breadcrumb,
    scrub_event,
    scrub_transaction,
    scrub_url,
)
from app.db.session import get_db_session
from app.main import api_app, app
from tests.database_doubles import UnreachableDatabaseSession
from tests.settings_factory import make_settings

FAKE_DSN: str = "https://public-key@sentry.example.invalid/1"


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


def test_sentry_settings_default_to_disabled() -> None:
    settings: Settings = make_settings()

    assert settings.sentry_dsn is None
    assert settings.sentry_environment == "local"
    assert settings.sentry_traces_sample_rate == 0


def test_an_empty_dsn_means_no_dsn() -> None:
    assert make_settings(sentry_dsn="").sentry_dsn is None


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
    assert options["before_send"] is scrub_event
    assert options["before_send_transaction"] is scrub_transaction
    assert options["before_breadcrumb"] is scrub_breadcrumb


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


def test_a_server_error_response_is_sent_only_through_its_error_log(
    transport: CapturingTransport,
) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))
    api_app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response: Response = TestClient(app).get("/api/health/db")
    sentry_sdk.flush()

    assert response.status_code == 503
    assert len(transport.events) == 1
    event: Event = transport.events[0]
    assert event.get("logentry", {}).get("message") == "Échec de la connexion à la base de données"


class FailingGameResultsService:
    def results(self, public_token: str, include_absent_votes: bool) -> None:
        raise RuntimeError("results failed")


def test_an_unhandled_error_on_a_results_link_hides_its_token(
    transport: CapturingTransport,
) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))
    api_app.dependency_overrides[get_game_results_service] = FailingGameResultsService

    response: Response = TestClient(app).get("/api/results/s3cr3t-token?include_absent_votes=0")
    sentry_sdk.flush()

    assert response.status_code == 500
    assert len(transport.events) == 1
    event: Event = transport.events[0]
    assert "s3cr3t-token" not in str(event)
    assert event.get("logentry", {}).get("formatted") == (
        "Erreur non gérée sur GET /api/results/[Filtered]"
    )
    assert event.get("request", {}).get("url") == "http://testserver/api/results/[Filtered]"


def test_the_access_log_of_uvicorn_leaves_no_breadcrumb(transport: CapturingTransport) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))

    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/1.1" %d', "203.0.113.7", "GET", "/moderation/accounts?query=a@b.c", 200
    )
    logging.getLogger("app.example").error("Erreur")
    sentry_sdk.flush()

    assert len(transport.events) == 1
    assert "203.0.113.7" not in str(transport.events[0])


def test_a_warning_is_not_sent_to_sentry(transport: CapturingTransport) -> None:
    configure_sentry(make_settings(sentry_dsn=FAKE_DSN))

    logging.getLogger("app.example").warning("Avertissement")
    sentry_sdk.flush()

    assert transport.events == []


def test_the_request_keeps_only_its_masked_url_method_and_user_agent() -> None:
    event: Event = {
        "request": {
            "url": "https://tierlist.test/api/results/s3cr3t",
            "method": "GET",
            "query_string": "code=s3cr3t",
            "cookies": {"refresh_token": "[Filtered]"},
            "headers": {
                "User-Agent": "Firefox",
                "Cf-Connecting-Ip": "203.0.113.7",
                "Referer": "https://tierlist.test/reset-password?token=s3cr3t",
            },
        }
    }

    cleaned: Event = scrub_event(event, {})

    assert cleaned.get("request") == {
        "url": "https://tierlist.test/api/results/[Filtered]",
        "method": "GET",
        "headers": {"User-Agent": "Firefox"},
    }


@pytest.mark.parametrize(
    ("url", "scrubbed"),
    [
        ("/api/results/s3cr3t", "/api/results/[Filtered]"),
        (
            "https://tierlist.test/api/rooms/K7P2QX/join",
            "https://tierlist.test/api/rooms/[Filtered]/join",
        ),
        ("/r/K7P2QX#guest=s3cr3t", "/r/[Filtered]"),
        ("/R/K7P2QX", "/R/[Filtered]"),
        ("https://oauth2.googleapis.com/token?code=s3cr3t", "https://oauth2.googleapis.com/token"),
        ("/api/templates/42/rooms", "/api/templates/42/rooms"),
    ],
)
def test_a_url_loses_its_query_its_fragment_and_its_secret_segments(
    url: str, scrubbed: str
) -> None:
    assert scrub_url(url) == scrubbed


def test_a_secret_segment_is_masked_inside_a_text() -> None:
    assert mask_secret_paths("Erreur sur GET /api/rooms/K7P2QX/game ?") == (
        "Erreur sur GET /api/rooms/[Filtered]/game ?"
    )


def test_an_email_address_is_masked_inside_a_text() -> None:
    database_error: str = "DETAIL:  Key (email)=(alice.martin+tl@example.co.uk) already exists."

    assert mask_secrets_in_text(database_error) == (
        "DETAIL:  Key (email)=([Filtered]) already exists."
    )


def test_a_long_text_without_email_is_masked_in_linear_time() -> None:
    long_identifier: str = "a" * 100_000

    started_at: float = time.perf_counter()
    masked: str = mask_secrets_in_text(long_identifier)

    assert masked == long_identifier
    assert time.perf_counter() - started_at < 1


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        (
            "Lien https://tierlist.test/r/K7P2QX#guest=s3cr3t invalide",
            "Lien https://tierlist.test/r/[Filtered]#guest=[Filtered] invalide",
        ),
        (
            "Envoi de https://tierlist.test/reset-password?token=s3cr3t&x=1",
            "Envoi de https://tierlist.test/reset-password?token=[Filtered]&x=1",
        ),
        ("/verify-email?TOKEN=s3cr3t", "/verify-email?TOKEN=[Filtered]"),
    ],
)
def test_a_secret_link_parameter_is_masked_inside_a_text(text: str, masked: str) -> None:
    assert mask_secrets_in_text(text) == masked


def test_an_error_event_loses_the_secrets_of_its_transaction_name() -> None:
    event: Event = {"transaction": "/api/results/s3cr3t"}

    assert scrub_event(event, {}).get("transaction") == "/api/results/[Filtered]"


def test_an_http_breadcrumb_loses_its_query_and_its_secret_segments() -> None:
    breadcrumb: dict[str, Any] = {
        "type": "http",
        "message": "GET /api/results/s3cr3t",
        "data": {
            "url": "https://tierlist.test/api/results/s3cr3t",
            "http.query": "include_absent_votes=0",
            "http.fragment": "top",
            "http.method": "GET",
        },
    }

    assert scrub_breadcrumb(breadcrumb, {}) == {
        "type": "http",
        "message": "GET /api/results/[Filtered]",
        "data": {"url": "https://tierlist.test/api/results/[Filtered]", "http.method": "GET"},
    }


def test_a_transaction_loses_the_secrets_of_its_name_and_spans() -> None:
    transaction: Event = {
        "type": "transaction",
        "transaction": "/api/rooms/K7P2QX",
        "spans": [
            {
                "op": "http.client",
                "description": "GET https://oauth2.googleapis.com/token?code=s3cr3t",
                "data": {"url": "https://oauth2.googleapis.com/token", "http.query": "code=s3cr3t"},
            }
        ],
    }

    scrubbed: Event = scrub_transaction(transaction, {})

    assert scrubbed.get("transaction") == "/api/rooms/[Filtered]"
    assert scrubbed.get("spans") == [
        {
            "op": "http.client",
            "description": "GET https://oauth2.googleapis.com/token",
            "data": {"url": "https://oauth2.googleapis.com/token"},
        }
    ]


def test_a_database_span_keeps_its_query_whole() -> None:
    query: str = "SELECT data #> '{a}' FROM t WHERE data ? 'key' AND id = %(id)s"
    transaction: Event = {"type": "transaction", "spans": [{"op": "db", "description": query}]}

    assert scrub_transaction(transaction, {}).get("spans") == [{"op": "db", "description": query}]


def test_an_event_without_request_is_left_unchanged() -> None:
    event: Event = {"message": "nightly purge failed"}

    assert scrub_event(event, {}) == {"message": "nightly purge failed"}


@pytest.mark.parametrize(
    ("sentry_settings", "expected_config"),
    [
        (
            {"app_release": "v1.2.3"},
            {"sentry_dsn": None, "environment": "local", "release": "v1.2.3"},
        ),
        (
            {"sentry_dsn": FAKE_DSN, "sentry_environment": "production", "app_release": "v2.0.0"},
            {"sentry_dsn": FAKE_DSN, "environment": "production", "release": "v2.0.0"},
        ),
    ],
)
def test_client_config_sends_the_sentry_settings(
    sentry_settings: dict[str, object], expected_config: dict[str, object]
) -> None:
    api_app.dependency_overrides[get_settings] = lambda: make_settings(**sentry_settings)

    response: Response = TestClient(app).get("/api/client-config")

    assert response.status_code == 200
    assert response.json() == expected_config
