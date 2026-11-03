import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateModeration
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from tests.integration.helpers import (
    JsonObject,
    create_room,
    create_template,
    next_item,
    register,
    register_super_admin,
    start_game,
)

pytestmark = pytest.mark.integration

TEMPLATE_ACTIONS: tuple[str, ...] = ("hide", "unhide", "delete")


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice)


def moderate(
    client: TestClient,
    headers: dict[str, str],
    action: str,
    template_id: str | uuid.UUID,
    reason: str = "Harassment",
) -> Response:
    return client.post(
        f"/moderation/templates/{template_id}/{action}", json={"reason": reason}, headers=headers
    )


def stored_template(db_session: Session, template_id: str) -> Template:
    db_session.expire_all()
    template: Template | None = db_session.get(Template, uuid.UUID(template_id))
    assert template is not None
    return template


def logged_actions(db_session: Session) -> list[ModerationAction]:
    return list(db_session.scalars(select(ModerationAction)).all())


def set_hidden(db_session: Session, template_id: str) -> None:
    template: Template = stored_template(db_session, template_id)
    template.moderation = TemplateModeration.HIDDEN
    template.moderation_reason = "Harassment"
    db_session.flush()


def test_hiding_a_template_keeps_the_reason_for_its_owner_and_logs_the_action(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    updated_at: datetime = stored_template(db_session, template_id).updated_at

    response: Response = moderate(auth_client, nina, "hide", template_id, "  Harassment  ")

    assert response.status_code == 204
    template: Template = stored_template(db_session, template_id)
    assert (template.moderation, template.moderation_reason) == (
        TemplateModeration.HIDDEN,
        "Harassment",
    )
    # Une décision de la modération n'est pas une modification du propriétaire
    assert template.updated_at == updated_at
    [entry] = logged_actions(db_session)
    assert (entry.action, entry.target_type, entry.target_id, entry.target_label) == (
        ModerationActionKind.HIDE,
        ModerationTargetType.TEMPLATE,
        template.id,
        "Food",
    )
    assert (entry.actor_name, entry.reason) == ("nina", "Harassment")


def test_the_owner_still_reads_and_edits_a_hidden_template(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    moderate(auth_client, nina, "hide", template_id)

    detail: Response = auth_client.get(f"/templates/{template_id}", headers=alice)
    listed: JsonObject = auth_client.get("/templates", headers=alice).json()["items"][0]
    renamed: Response = auth_client.patch(
        f"/templates/{template_id}", json={"name": "Snacks"}, headers=alice
    )

    assert detail.status_code == 200
    assert (detail.json()["moderation"], detail.json()["moderation_reason"]) == (
        "hidden",
        "Harassment",
    )
    assert (listed["moderation"], listed["moderation_reason"]) == ("hidden", "Harassment")
    assert renamed.status_code == 200


def test_unhiding_a_template_gives_it_back_to_its_owner(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    template_id: str,
):
    set_hidden(db_session, template_id)

    response: Response = moderate(auth_client, nina, "unhide", template_id, "Appeal accepted")

    assert response.status_code == 204
    template: Template = stored_template(db_session, template_id)
    assert (template.moderation, template.moderation_reason) == (TemplateModeration.NONE, None)
    [entry] = logged_actions(db_session)
    assert (entry.action, entry.reason) == (ModerationActionKind.UNHIDE, "Appeal accepted")


@pytest.mark.parametrize("hidden", [False, True])
def test_deleting_a_template_is_a_soft_deletion_like_its_owner_would_do(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
    hidden: bool,
):
    if hidden:
        set_hidden(db_session, template_id)

    response: Response = moderate(auth_client, nina, "delete", template_id)

    assert response.status_code == 204
    assert stored_template(db_session, template_id).deleted_at is not None
    assert auth_client.get(f"/templates/{template_id}", headers=alice).status_code == 404
    [entry] = logged_actions(db_session)
    assert entry.action == ModerationActionKind.DELETE


@pytest.mark.parametrize(
    ("action", "state"),
    [
        ("hide", "hidden"),
        ("hide", "deleted"),
        ("unhide", "visible"),
        ("unhide", "deleted"),
        ("delete", "deleted"),
    ],
)
def test_an_action_that_does_not_apply_to_the_state_is_refused(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    template_id: str,
    action: str,
    state: str,
):
    if state == "hidden":
        set_hidden(db_session, template_id)
    if state == "deleted":
        stored_template(db_session, template_id).deleted_at = datetime.now(UTC)
        db_session.flush()

    response: Response = moderate(auth_client, nina, action, template_id)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_MODERATION_CONFLICT
    assert logged_actions(db_session) == []


@pytest.mark.parametrize("action", TEMPLATE_ACTIONS)
def test_an_unknown_or_purged_template_is_not_found(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], action: str
):
    response: Response = moderate(auth_client, nina, action, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND
    assert logged_actions(db_session) == []


@pytest.mark.parametrize("action", TEMPLATE_ACTIONS)
def test_the_template_actions_require_a_session(auth_client: TestClient, action: str):
    response: Response = auth_client.post(
        f"/moderation/templates/{uuid.uuid4()}/{action}", json={"reason": "Harassment"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


@pytest.mark.parametrize("action", TEMPLATE_ACTIONS)
def test_the_template_actions_refuse_other_accounts(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    template_id: str,
    action: str,
):
    response: Response = moderate(auth_client, alice, action, template_id)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.SUPER_ADMIN_REQUIRED
    assert stored_template(db_session, template_id).moderation == TemplateModeration.NONE


@pytest.mark.parametrize("reason", ["", "   ", "x" * (MODERATION_REASON_MAX_LENGTH + 1)])
def test_an_action_needs_a_reason_of_at_most_500_characters(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    template_id: str,
    reason: str,
):
    response: Response = moderate(auth_client, nina, "hide", template_id, reason)

    assert response.status_code == 422
    assert stored_template(db_session, template_id).moderation == TemplateModeration.NONE


def test_a_hidden_template_cannot_open_a_room(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    template_id: str,
):
    set_hidden(db_session, template_id)

    response: Response = auth_client.post(
        "/rooms", json={"template_id": template_id}, headers=alice
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HIDDEN


def test_a_hidden_template_cannot_start_a_game_until_it_is_unhidden(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    room: JsonObject = create_room(auth_client, alice, template_id)
    moderate(auth_client, nina, "hide", template_id)

    refused: Response = auth_client.post(f"/rooms/{room['code']}/game", headers=alice)
    lobby: JsonObject = auth_client.get(f"/rooms/{room['code']}", headers=alice).json()
    moderate(auth_client, nina, "unhide", template_id)
    started: Response = auth_client.post(f"/rooms/{room['code']}/game", headers=alice)

    assert refused.status_code == 409
    assert refused.json()["code"] == ErrorCode.TEMPLATE_HIDDEN
    assert lobby["template"]["hidden"] is True
    assert started.status_code == 201


def test_a_game_in_progress_finishes_after_its_template_is_hidden(
    auth_client: TestClient,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    room: JsonObject = create_room(auth_client, alice, template_id)
    start_game(auth_client, room["code"], alice)

    moderate(auth_client, nina, "hide", template_id)

    following: JsonObject = next_item(auth_client, room["code"], alice)
    assert following["game"]["round_number"] == 2
