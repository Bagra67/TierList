import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.models.enums import ModerationActionKind, ReportStatus
from app.models.moderation_action import ModerationAction
from app.models.report import Report
from app.models.template import Template
from app.models.template_like import TemplateLike
from app.models.tile import Tile
from app.models.user import User
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
    create_public_template,
    create_template,
    delete_template,
    register,
    register_super_admin,
    send_report,
    stored_template,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"
BOB_EMAIL = "bob@example.com"
RETENTION = timedelta(days=get_settings().deleted_template_retention_days)


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, ALICE_EMAIL)


def deleted_template(
    client: TestClient,
    db_session: Session,
    owner: dict[str, str],
    name: str,
    deleted_days_ago: int,
) -> str:
    template_id: str = create_template(client, db_session, owner)
    delete_template(client, template_id, owner)
    template: Template = stored_template(db_session, template_id)
    template.name = name
    template.deleted_at = datetime.now(UTC) - timedelta(days=deleted_days_ago)
    db_session.flush()
    return template_id


def moderate(
    client: TestClient, headers: dict[str, str], action: str, template_id: str | uuid.UUID
) -> Response:
    url: str = f"/moderation/templates/{template_id}/{action}"
    return client.post(url, json={"reason": "Illicite"}, headers=headers)


def list_deleted(
    client: TestClient, headers: dict[str, str], **params: str | int
) -> list[JsonObject]:
    response: Response = client.get("/moderation/templates/deleted", params=params, headers=headers)
    assert response.status_code == 200
    return response.json()["templates"]


def names(templates: list[JsonObject]) -> list[str]:
    return [template["name"] for template in templates]


def test_the_list_shows_only_deleted_templates_the_closest_to_the_purge_first(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    create_template(auth_client, db_session, alice)
    recent_id: str = deleted_template(auth_client, db_session, alice, "Recent", 2)
    deleted_template(auth_client, db_session, alice, "Old", 25)

    templates: list[JsonObject] = list_deleted(auth_client, nina)

    assert names(templates) == ["Old", "Recent"]
    recent: JsonObject = templates[1]
    template: Template = stored_template(db_session, recent_id)
    assert template.deleted_at is not None
    assert (recent["owner_name"], recent["tile_count"], recent["deletion_reason"]) == (
        "alice",
        3,
        None,
    )
    assert datetime.fromisoformat(recent["erase_at"]) == template.deleted_at + RETENTION


def test_the_list_gives_the_reason_of_a_deletion_by_the_moderation(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)
    assert moderate(auth_client, nina, "delete", template_id).status_code == 204

    [template] = list_deleted(auth_client, nina)

    assert template["deletion_reason"] == "Illicite"


def test_a_template_restored_then_deleted_by_its_owner_shows_no_moderation_reason(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)
    moderate(auth_client, nina, "delete", template_id)
    assert moderate(auth_client, nina, "restore", template_id).status_code == 204
    delete_template(auth_client, template_id, alice)

    [template] = list_deleted(auth_client, nina)

    assert template["deletion_reason"] is None
    assert auth_client.get("/templates/removed", headers=alice).json() == {"items": []}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"owner": "BOB@"}, ["Bob's"], id="owner email"),
        pytest.param({"owner": "ali"}, ["Spices", "Cheeses"], id="owner name"),
        pytest.param({"name": "chee"}, ["Cheeses"], id="name"),
        pytest.param({"deleted_days_ago_after": 10}, ["Cheeses", "Bob's"], id="deleted after"),
        pytest.param({"deleted_days_ago_before": 10}, ["Spices"], id="deleted before"),
    ],
)
def test_the_list_filters_on_the_owner_the_name_and_the_deletion_date(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    params: dict[str, str | int],
    expected: list[str],
):
    bob: dict[str, str] = register(auth_client, "bob@example.com")
    deleted_template(auth_client, db_session, alice, "Spices", 20)
    deleted_template(auth_client, db_session, alice, "Cheeses", 5)
    deleted_template(auth_client, db_session, bob, "Bob's", 1)
    query: dict[str, str | int] = dict(params)
    for key, bound in (
        ("deleted_days_ago_after", "deleted_after"),
        ("deleted_days_ago_before", "deleted_before"),
    ):
        if key in query:
            days: int = int(query.pop(key))
            query[bound] = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    assert names(list_deleted(auth_client, nina, **query)) == expected


def test_the_list_is_paginated(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    for days_ago in (3, 2, 1):
        deleted_template(auth_client, db_session, alice, f"Deleted {days_ago}", days_ago)

    first: Response = auth_client.get(
        "/moderation/templates/deleted", params={"limit": 2}, headers=nina
    )
    second: Response = auth_client.get(
        "/moderation/templates/deleted", params={"limit": 2, "offset": 2}, headers=nina
    )

    assert names(first.json()["templates"]) == ["Deleted 3", "Deleted 2"]
    assert first.json()["has_more"] is True
    assert names(second.json()["templates"]) == ["Deleted 1"]
    assert second.json()["has_more"] is False


def test_the_list_runs_a_fixed_number_of_queries(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    def queries_for_the_list() -> int:
        with counted_queries(db_session) as statements:
            list_deleted(auth_client, nina)
        return len(statements)

    deleted_template(auth_client, db_session, alice, "First", 1)
    one: int = queries_for_the_list()
    for days_ago in (2, 3, 4):
        template_id: str = deleted_template(auth_client, db_session, alice, "More", days_ago)
        moderate(auth_client, nina, "restore", template_id)
        moderate(auth_client, nina, "delete", template_id)

    assert queries_for_the_list() == one


def test_the_review_of_a_deleted_template_gives_its_deletion(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)
    moderate(auth_client, nina, "delete", template_id)

    body: JsonObject = auth_client.get(f"/moderation/templates/{template_id}", headers=nina).json()

    template: Template = stored_template(db_session, template_id)
    assert template.deleted_at is not None
    assert datetime.fromisoformat(body["deleted_at"]) == template.deleted_at
    assert datetime.fromisoformat(body["erase_at"]) == template.deleted_at + RETENTION
    assert body["deletion_reason"] == "Illicite"
    assert len(body["tiles"]) == 3


def test_restoring_gives_the_template_back_to_its_owner_and_logs_the_action(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice)
    moderate(auth_client, nina, "delete", template_id)

    response: Response = moderate(auth_client, nina, "restore", template_id)

    assert response.status_code == 204
    assert stored_template(db_session, template_id).deleted_at is None
    assert auth_client.get(f"/templates/{template_id}", headers=alice).status_code == 200
    assert auth_client.get("/templates/removed", headers=alice).json() == {"items": []}
    assert list_deleted(auth_client, nina) == []
    last: ModerationAction | None = db_session.scalars(
        select(ModerationAction).order_by(ModerationAction.created_at.desc())
    ).first()
    assert last is not None
    assert (last.action, last.target_label, last.reason) == (
        ModerationActionKind.RESTORE,
        "Food",
        "Illicite",
    )


def test_permanently_deleting_erases_the_template_and_logs_the_action(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_public_template(auth_client, db_session, alice, ALICE_EMAIL)
    bob: dict[str, str] = register(auth_client, BOB_EMAIL)
    send_report(auth_client, "template", template_id, bob)
    bob_id: uuid.UUID = db_session.scalars(select(User.id).where(User.email == BOB_EMAIL)).one()
    db_session.add(TemplateLike(template_id=uuid.UUID(template_id), user_id=bob_id))
    db_session.flush()
    delete_template(auth_client, template_id, alice)

    response: Response = moderate(auth_client, nina, "purge", template_id)

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Template, uuid.UUID(template_id)) is None
    for model in (Tile, TemplateLike):
        assert (
            db_session.scalar(
                select(func.count())
                .select_from(model)
                .where(model.template_id == uuid.UUID(template_id))
            )
            == 0
        )
    purge: ModerationAction = db_session.scalars(
        select(ModerationAction).where(ModerationAction.action == ModerationActionKind.PURGE)
    ).one()
    assert (purge.target_id, purge.target_label) == (uuid.UUID(template_id), "Food")
    report: Report = db_session.scalars(select(Report)).one()
    assert (report.status, report.closed_by_action_id) == (ReportStatus.ACTIONED, purge.id)


@pytest.mark.parametrize("action", ["restore", "purge"])
def test_restoring_or_erasing_a_template_that_is_not_deleted_is_a_conflict(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    action: str,
):
    template_id: str = create_template(auth_client, db_session, alice)

    response: Response = moderate(auth_client, nina, action, template_id)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_MODERATION_CONFLICT


@pytest.mark.parametrize("action", ["restore", "purge"])
def test_restoring_or_erasing_an_unknown_template_is_not_found(
    auth_client: TestClient, nina: dict[str, str], action: str
):
    response: Response = moderate(auth_client, nina, action, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


@pytest.mark.parametrize("action", ["restore", "purge"])
def test_only_super_admins_restore_or_erase_a_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], action: str
):
    template_id: str = deleted_template(auth_client, db_session, alice, "Mine", 1)

    response: Response = moderate(auth_client, alice, action, template_id)

    assert response.status_code == 403
    assert stored_template(db_session, template_id).deleted_at is not None
