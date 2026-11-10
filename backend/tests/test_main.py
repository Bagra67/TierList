import asyncio
import inspect
from collections.abc import Iterator

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import BaseRoute

import app.main as main_module
from app.api.routes import (
    auth,
    history,
    images,
    moderation,
    results,
    room_channel,
    rooms,
    templates,
)
from app.db.session import get_db_session
from app.main import api_app, app
from app.services.round_timers import round_timers
from tests.database_doubles import UnreachableDatabaseSession

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    api_app.dependency_overrides.clear()


def test_health_answers_without_touching_the_database():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "release": "dev"}


def test_health_db_ok():
    engine = create_engine("sqlite://")

    def sqlite_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    api_app.dependency_overrides[get_db_session] = sqlite_session

    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "release": "dev"}


def test_health_answers_when_the_database_is_down():
    api_app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response: Response = client.get("/api/health")

    assert response.status_code == 200


def test_health_db_unavailable():
    api_app.dependency_overrides[get_db_session] = UnreachableDatabaseSession

    response = client.get("/api/health/db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable", "code": "database_unavailable"}


def test_unknown_api_route_is_a_json_404():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "http_error"


def test_api_routes_are_only_served_under_the_prefix():
    assert client.get("/health").status_code == 404


def test_a_path_outside_the_api_uses_the_error_format():
    response: Response = client.get("/health")

    assert response.json() == {"detail": "Not Found", "code": "http_error"}


def test_http_routes_do_not_run_on_the_event_loop():
    all_routes: list[BaseRoute] = [
        *api_app.routes,
        *auth.router.routes,
        *history.router.routes,
        *images.router.routes,
        *moderation.router.routes,
        *results.router.routes,
        *room_channel.router.routes,
        *rooms.router.routes,
        *templates.router.routes,
    ]
    coroutine_routes: list[str] = [
        route.path
        for route in all_routes
        if isinstance(route, APIRoute) and inspect.iscoroutinefunction(route.endpoint)
    ]

    assert coroutine_routes == []


def test_the_root_app_adds_no_task_per_request():
    middleware_classes: list[object] = [middleware.cls for middleware in app.user_middleware]

    assert BaseHTTPMiddleware not in middleware_classes


def test_the_timers_start_before_the_deadlines_are_scheduled_again(
    monkeypatch: pytest.MonkeyPatch,
):
    startup_steps: list[str] = []

    def record_timers_start(
        loop: asyncio.AbstractEventLoop, *handlers: object, **named_handlers: object
    ) -> None:
        startup_steps.append("timers started")

    def record_reschedule(*args: object) -> None:
        startup_steps.append("deadlines scheduled")

    def skip_presence_reset(*args: object) -> None:
        return None

    monkeypatch.setattr(main_module, "_reset_presence", skip_presence_reset)
    monkeypatch.setattr(main_module, "_reschedule_rounds", record_reschedule)
    monkeypatch.setattr(round_timers, "start", record_timers_start)

    with TestClient(app):
        assert startup_steps == ["timers started", "deadlines scheduled"]
