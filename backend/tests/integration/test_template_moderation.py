import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.core.config import get_settings
from app.models.enums import ModerationActionKind, ModerationTargetType, TemplateModeration
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.services.maintenance import purge_moderation_log
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
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
    response: Response = moderate(auth_client, nina, "hide", template_id, "  Harassment  ")

    assert response.status_code == 204
    template: Template = stored_template(db_session, template_id)
    assert (template.moderation, template.moderation_reason) == (
        TemplateModeration.HIDDEN,
        "Harassment",
    )
    [entry] = logged_actions(db_session)
    assert (entry.action, entry.target_type, entry.target_id, entry.target_label) == (
        ModerationActionKind.HIDE,
        ModerationTargetType.TEMPLATE,
        template.id,
        "Food",
    )
    assert (entry.actor_name, entry.reason) == ("nina", "Harassment")


def test_hiding_a_template_does_not_count_as_a_change_by_its_owner(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], template_id: str
):
    updated_at: datetime = stored_template(db_session, template_id).updated_at

    moderate(auth_client, nina, "hide", template_id, "Harassment")

    assert stored_template(db_session, template_id).updated_at == updated_at


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


def test_the_hiding_reason_outlives_the_purge_of_the_log(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    moderate(auth_client, nina, "hide", template_id, "Harassment")
    [entry] = logged_actions(db_session)
    retention_days: int = get_settings().moderation_log_retention_days
    entry.created_at = datetime.now(UTC) - timedelta(days=retention_days + 1)
    db_session.flush()

    purge_moderation_log(lambda: nullcontext(db_session), get_settings())

    assert logged_actions(db_session) == []
    detail: Response = auth_client.get(f"/templates/{template_id}", headers=alice)
    assert detail.json()["moderation_reason"] == "Harassment"


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


def add_tile_with_image(
    client: TestClient,
    db_session: Session,
    headers: dict[str, str],
    template_id: str,
    text: str | None,
) -> tuple[str, Image]:
    template: Template = stored_template(db_session, template_id)
    image: Image = Image(
        owner_id=template.owner_id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="a" * 64,
    )
    db_session.add(image)
    db_session.flush()
    response: Response = client.post(
        f"/templates/{template_id}/tiles",
        json={"text": text, "image_id": str(image.id)},
        headers=headers,
    )
    assert response.status_code == 201
    tile_id: str = response.json()["tiles"][-1]["id"]
    return tile_id, image


def moderate_image(
    client: TestClient, headers: dict[str, str], action: str, image: Image, reason: str
) -> None:
    response: Response = client.post(
        f"/moderation/images/{image.id}/{action}", json={"reason": reason}, headers=headers
    )
    assert response.status_code == 204


def test_the_owner_sees_the_decision_about_an_image_on_its_tile(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    tile_id, image = add_tile_with_image(auth_client, db_session, alice, template_id, "Paprika")
    stored_images[image.storage_key] = b"webp"
    moderate_image(auth_client, nina, "hide", image, "Violence")

    template: Response = auth_client.get(f"/templates/{template_id}", headers=alice)

    [tile] = [tile for tile in template.json()["tiles"] if tile["id"] == tile_id]
    assert tile["image_removed"] is True
    assert tile["image_status"] == "hidden"
    assert tile["image_moderation_reason"] == "Violence"


def test_my_templates_lists_the_removed_images_of_each_template_only(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_template(auth_client, db_session, alice)
    hidden_tile_id, hidden_image = add_tile_with_image(
        auth_client, db_session, alice, template_id, "Paprika"
    )
    deleted_tile_id, deleted_image = add_tile_with_image(
        auth_client, db_session, alice, template_id, None
    )
    add_tile_with_image(auth_client, db_session, alice, other_template_id, "Visible")
    stored_images[hidden_image.storage_key] = b"webp"
    stored_images[deleted_image.storage_key] = b"webp"
    moderate_image(auth_client, nina, "hide", hidden_image, "Violence")
    moderate_image(auth_client, nina, "delete", deleted_image, "Illegal content")

    items: list[JsonObject] = auth_client.get("/templates", headers=alice).json()["items"]

    summaries: dict[str, JsonObject] = {item["id"]: item for item in items}
    removed_images: list[JsonObject] = summaries[template_id]["removed_images"]
    assert [(image["tile_id"], image["status"], image["reason"]) for image in removed_images] == [
        (hidden_tile_id, "hidden", "Violence"),
        (deleted_tile_id, "deleted", "Illegal content"),
    ]
    assert removed_images[0]["tile_text"] == "Paprika"
    assert removed_images[1]["tile_text"] is None
    assert summaries[other_template_id]["removed_images"] == []


def test_my_templates_reads_the_removed_images_in_a_constant_number_of_queries(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    other_template_id: str = create_template(auth_client, db_session, alice)

    def hide_an_image_of_each_template() -> None:
        for owned_template_id in (template_id, other_template_id):
            _, image = add_tile_with_image(
                auth_client, db_session, alice, owned_template_id, "Paprika"
            )
            stored_images[image.storage_key] = b"webp"
            moderate_image(auth_client, nina, "hide", image, "Violence")

    hide_an_image_of_each_template()
    with counted_queries(db_session) as statements_with_two_images:
        auth_client.get("/templates", headers=alice)

    hide_an_image_of_each_template()
    with counted_queries(db_session) as statements_with_four_images:
        items: list[JsonObject] = auth_client.get("/templates", headers=alice).json()["items"]

    assert len(statements_with_four_images) == len(statements_with_two_images)
    assert [len(item["removed_images"]) for item in items] == [2, 2]


def test_an_unhidden_image_leaves_the_removed_images(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    _, image = add_tile_with_image(auth_client, db_session, alice, template_id, "Paprika")
    stored_images[image.storage_key] = b"webp"
    moderate_image(auth_client, nina, "hide", image, "Violence")
    moderate_image(auth_client, nina, "unhide", image, "Mistake")

    [summary] = auth_client.get("/templates", headers=alice).json()["items"]

    assert summary["removed_images"] == []


def test_the_owner_sees_a_template_deleted_by_the_moderation_with_its_reason(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    name: str = stored_template(db_session, template_id).name
    moderate(auth_client, nina, "delete", template_id, "Illegal content")

    response: Response = auth_client.get("/templates/removed", headers=alice)

    assert response.status_code == 200
    [removed] = response.json()["items"]
    assert removed["id"] == template_id
    assert removed["name"] == name
    assert removed["reason"] == "Illegal content"
    assert set(removed) == {"id", "name", "removed_at", "reason"}


def test_a_template_deleted_by_its_owner_is_not_a_moderation_decision(
    auth_client: TestClient, alice: dict[str, str], template_id: str
):
    assert auth_client.delete(f"/templates/{template_id}", headers=alice).status_code == 204

    response: Response = auth_client.get("/templates/removed", headers=alice)

    assert response.json()["items"] == []


def test_a_hidden_template_is_not_among_the_removed_ones(
    auth_client: TestClient,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    moderate(auth_client, nina, "hide", template_id)

    assert auth_client.get("/templates/removed", headers=alice).json()["items"] == []


def test_a_template_deleted_by_the_moderation_leaves_the_list_once_purged(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    template_id: str,
):
    moderate(auth_client, nina, "delete", template_id)
    db_session.delete(stored_template(db_session, template_id))
    db_session.flush()

    assert auth_client.get("/templates/removed", headers=alice).json()["items"] == []


def test_the_templates_deleted_by_the_moderation_stay_private_to_their_owner(
    auth_client: TestClient,
    nina: dict[str, str],
    template_id: str,
):
    moderate(auth_client, nina, "delete", template_id)
    bob: dict[str, str] = register(auth_client, "bob@example.com")

    assert auth_client.get("/templates/removed", headers=bob).json()["items"] == []


def test_the_templates_deleted_by_the_moderation_require_a_session(auth_client: TestClient):
    assert auth_client.get("/templates/removed").status_code == 401
