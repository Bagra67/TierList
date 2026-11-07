from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.moderation_action import ModerationAction
from app.models.user import User
from tests.integration.helpers import JsonObject, register, register_super_admin

pytestmark = pytest.mark.integration

MODERATION_ROUTES: tuple[str, ...] = ("/moderation/log", "/moderation/super-admins")


def account(db_session: Session, email: str) -> User:
    return db_session.scalars(select(User).where(User.email == email)).one()


def add_entry(
    db_session: Session, actor: User, target_label: str, minutes_ago: int
) -> ModerationAction:
    entry: ModerationAction = ModerationAction(
        actor_id=actor.id,
        actor_name=actor.display_name,
        action=ModerationActionKind.HIDE,
        target_type=ModerationTargetType.TEMPLATE,
        target_id=None,
        target_label=target_label,
        reason="Harassment",
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    db_session.add(entry)
    db_session.flush()
    return entry


def labels(response: Response) -> list[str]:
    return [entry["target_label"] for entry in response.json()["entries"]]


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.mark.parametrize("path", MODERATION_ROUTES)
def test_the_moderation_routes_require_a_session(auth_client: TestClient, path: str):
    response: Response = auth_client.get(path)

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


@pytest.mark.parametrize("path", MODERATION_ROUTES)
def test_the_moderation_routes_refuse_other_accounts(auth_client: TestClient, path: str):
    headers: dict[str, str] = register(auth_client, "alice@example.com")

    response: Response = auth_client.get(path, headers=headers)

    assert response.status_code == 403
    assert response.json() == {
        "detail": messages.SUPER_ADMIN_REQUIRED,
        "code": ErrorCode.SUPER_ADMIN_REQUIRED,
    }


def test_the_log_lists_every_field_newest_first(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    actor: User = account(db_session, "nina@example.com")
    add_entry(db_session, actor, "Older", minutes_ago=10)
    newer: ModerationAction = add_entry(db_session, actor, "Newer", minutes_ago=1)

    response: Response = auth_client.get("/moderation/log", headers=nina)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert labels(response) == ["Newer", "Older"]
    assert body["has_more"] is False
    assert body["entries"][0] == {
        "id": str(newer.id),
        "created_at": body["entries"][0]["created_at"],
        "actor_id": str(actor.id),
        "actor_name": "nina",
        "action": "hide",
        "target_type": "template",
        "target_id": None,
        "target_label": "Newer",
        "reason": "Harassment",
    }


def test_the_log_is_paginated(auth_client: TestClient, db_session: Session, nina: dict[str, str]):
    actor: User = account(db_session, "nina@example.com")
    for minutes_ago in range(3):
        add_entry(db_session, actor, f"Entry {minutes_ago}", minutes_ago=minutes_ago)

    first: Response = auth_client.get("/moderation/log?limit=2", headers=nina)
    second: Response = auth_client.get("/moderation/log?limit=2&offset=2", headers=nina)

    assert labels(first) == ["Entry 0", "Entry 1"]
    assert first.json()["has_more"] is True
    assert labels(second) == ["Entry 2"]
    assert second.json()["has_more"] is False


def test_the_log_is_filtered_by_super_admin(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    register_super_admin(auth_client, db_session, "sam@example.com")
    sam: User = account(db_session, "sam@example.com")
    add_entry(db_session, account(db_session, "nina@example.com"), "By Nina", minutes_ago=2)
    add_entry(db_session, sam, "By Sam", minutes_ago=1)

    response: Response = auth_client.get(f"/moderation/log?actor_id={sam.id}", headers=nina)

    assert labels(response) == ["By Sam"]


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        pytest.param("top 10", ['Template "Top 10 teachers"'], id="case-insensitive"),
        pytest.param("100%", ["Account 100%"], id="percent-is-a-plain-character"),
    ],
)
def test_the_log_is_filtered_by_target(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    search: str,
    expected: list[str],
):
    actor: User = account(db_session, "nina@example.com")
    add_entry(db_session, actor, 'Template "Top 10 teachers"', minutes_ago=3)
    add_entry(db_session, actor, "Account 100%", minutes_ago=2)
    add_entry(db_session, actor, "Account 1000", minutes_ago=1)

    response: Response = auth_client.get("/moderation/log", params={"target": search}, headers=nina)

    assert labels(response) == expected


def test_the_super_admins_are_listed_by_name(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    register_super_admin(auth_client, db_session, "adam@example.com")
    register(auth_client, "alice@example.com")

    response: Response = auth_client.get("/moderation/super-admins", headers=nina)

    assert response.status_code == 200
    assert [user["display_name"] for user in response.json()] == ["adam", "nina"]
