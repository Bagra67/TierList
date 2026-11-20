import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.templates import (
    OFFICIAL_ACCOUNT_ID,
    OFFICIAL_TEMPLATE_MAX_TAGS,
    OFFICIAL_TEMPLATE_MAX_TILES,
)
from app.models.enums import ModerationActionKind
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.services.email import Email
from tests.integration.helpers import (
    JsonObject,
    ban_account,
    create_room,
    register,
    register_super_admin,
    stored_template,
)

pytestmark = pytest.mark.integration

NINA_EMAIL = "nina@example.com"


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, NINA_EMAIL)


@pytest.fixture
def omar(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "omar@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


def create_official(client: TestClient, headers: dict[str, str], name: str = "Cheeses") -> str:
    response: Response = client.post(
        "/moderation/official-templates", json={"name": name}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_tiles(db_session: Session, template_id: str, count: int) -> None:
    for position in range(count):
        db_session.add(
            Tile(template_id=uuid.UUID(template_id), text=f"Tile {position}", position=position)
        )
    db_session.flush()


def published_official(client: TestClient, db_session: Session, headers: dict[str, str]) -> str:
    template_id: str = create_official(client, headers)
    add_tiles(db_session, template_id, 3)
    response: Response = client.post(
        f"/moderation/official-templates/{template_id}/publish", headers=headers
    )
    assert response.status_code == 200
    return template_id


def expire_lease(db_session: Session, template_id: str) -> None:
    template: Template = stored_template(db_session, template_id)
    template.editing_until = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()


def logged_actions(db_session: Session, template_id: str) -> list[ModerationActionKind]:
    statement = (
        select(ModerationAction.action)
        .where(ModerationAction.target_id == uuid.UUID(template_id))
        .order_by(ModerationAction.created_at)
    )
    return list(db_session.scalars(statement).all())


def rename(client: TestClient, template_id: str, headers: dict[str, str]) -> Response:
    return client.patch(f"/templates/{template_id}", json={"name": "Renamed"}, headers=headers)


def marketplace_names(client: TestClient) -> list[str]:
    return [item["name"] for item in client.get("/marketplace/templates").json()["items"]]


def test_a_super_admin_creates_an_official_draft_owned_by_the_site(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    response: Response = auth_client.post(
        "/moderation/official-templates", json={"name": "Cheeses"}, headers=nina
    )

    assert response.status_code == 201
    body: JsonObject = response.json()
    assert body["official"] is True
    assert body["visibility"] == "private"
    assert body["featured"] is False
    assert body["editing_by_name"] == "nina"
    assert body["max_tiles"] == OFFICIAL_TEMPLATE_MAX_TILES
    assert body["max_tags"] == OFFICIAL_TEMPLATE_MAX_TAGS
    assert stored_template(db_session, body["id"]).owner_id == OFFICIAL_ACCOUNT_ID
    assert logged_actions(db_session, body["id"]) == [ModerationActionKind.CREATE]


def test_the_official_templates_are_listed_with_their_state_and_editor(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], omar: dict[str, str]
):
    draft_id: str = create_official(auth_client, nina, "Desserts")
    published_id: str = published_official(auth_client, db_session, omar)
    expire_lease(db_session, published_id)

    items: list[JsonObject] = auth_client.get(
        "/moderation/official-templates", headers=nina
    ).json()["items"]

    by_id: dict[str, JsonObject] = {item["id"]: item for item in items}
    assert by_id[draft_id]["visibility"] == "private"
    assert by_id[draft_id]["editing_by_name"] == "nina"
    assert by_id[published_id]["visibility"] == "public"
    assert by_id[published_id]["tile_count"] == 3
    assert by_id[published_id]["editing_by_name"] is None


def test_a_player_cannot_reach_the_official_templates(
    auth_client: TestClient, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)

    assert (
        auth_client.post(
            "/moderation/official-templates", json={"name": "X"}, headers=alice
        ).status_code
        == 403
    )
    assert auth_client.get(f"/templates/{template_id}", headers=alice).status_code == 404
    assert rename(auth_client, template_id, alice).status_code == 404


def test_the_super_admin_holding_the_lease_edits_the_template_and_the_edit_is_logged_once(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)
    expire_lease(db_session, template_id)
    assert (
        auth_client.post(
            f"/moderation/official-templates/{template_id}/lock", headers=nina
        ).status_code
        == 200
    )

    assert rename(auth_client, template_id, nina).status_code == 200
    assert rename(auth_client, template_id, nina).status_code == 200

    assert logged_actions(db_session, template_id) == [
        ModerationActionKind.CREATE,
        ModerationActionKind.EDIT,
    ]


def test_another_super_admin_cannot_edit_or_lock_while_the_lease_is_held(
    auth_client: TestClient, nina: dict[str, str], omar: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)

    lock: Response = auth_client.post(
        f"/moderation/official-templates/{template_id}/lock", headers=omar
    )
    edit: Response = rename(auth_client, template_id, omar)

    for response in (lock, edit):
        assert response.status_code == 409
        assert response.json()["code"] == ErrorCode.OFFICIAL_TEMPLATE_LOCKED
        assert response.json()["params"] == {"editor": "nina"}
    read: JsonObject = auth_client.get(f"/templates/{template_id}", headers=omar).json()
    assert read["editing_by_name"] == "nina"


def test_an_edit_without_the_lease_is_refused(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)
    expire_lease(db_session, template_id)

    response: Response = rename(auth_client, template_id, nina)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.OFFICIAL_TEMPLATE_LOCKED
    assert "params" not in response.json()


def test_another_super_admin_takes_the_lease_once_it_expires_or_is_given_back(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], omar: dict[str, str]
):
    expired_id: str = create_official(auth_client, nina, "Expired")
    expire_lease(db_session, expired_id)
    given_back_id: str = create_official(auth_client, nina, "Given back")
    assert (
        auth_client.delete(
            f"/moderation/official-templates/{given_back_id}/lock", headers=nina
        ).status_code
        == 204
    )

    for template_id in (expired_id, given_back_id):
        response: Response = auth_client.post(
            f"/moderation/official-templates/{template_id}/lock", headers=omar
        )
        assert response.status_code == 200
        assert response.json()["editing_by_name"] == "omar"


def test_giving_back_the_lease_of_another_super_admin_does_nothing(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], omar: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)

    auth_client.delete(f"/moderation/official-templates/{template_id}/lock", headers=omar)

    assert stored_template(db_session, template_id).editing_by is not None


def test_an_official_template_goes_past_the_limits_of_the_players(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)
    add_tiles(db_session, template_id, 40)
    tags: list[str] = [f"tag {index}" for index in range(OFFICIAL_TEMPLATE_MAX_TAGS)]

    tile: Response = auth_client.post(
        f"/templates/{template_id}/tiles", json={"text": "One more"}, headers=nina
    )
    tagged: Response = auth_client.put(
        f"/templates/{template_id}/tags", json={"tags": tags}, headers=nina
    )
    too_many_tags: Response = auth_client.put(
        f"/templates/{template_id}/tags", json={"tags": [*tags, "extra"]}, headers=nina
    )

    assert tile.status_code == 201
    assert len(tile.json()["tiles"]) == 41
    assert tagged.status_code == 200
    assert too_many_tags.status_code == 422


def test_an_official_template_has_at_most_its_own_number_of_tiles(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)
    add_tiles(db_session, template_id, OFFICIAL_TEMPLATE_MAX_TILES)

    response: Response = auth_client.post(
        f"/templates/{template_id}/tiles", json={"text": "One more"}, headers=nina
    )

    assert response.status_code == 409
    assert response.json()["params"] == {"max_tiles": OFFICIAL_TEMPLATE_MAX_TILES}


def test_a_draft_is_neither_listed_nor_playable(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)
    add_tiles(db_session, template_id, 3)

    assert marketplace_names(auth_client) == []
    assert auth_client.get(f"/marketplace/templates/{template_id}").status_code == 404
    response: Response = auth_client.post(
        "/rooms", json={"template_id": template_id}, headers=alice
    )
    assert response.status_code == 404


def test_a_published_official_template_is_signed_by_tierlist_and_playable(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    template_id: str = published_official(auth_client, db_session, nina)

    card: JsonObject = auth_client.get("/marketplace/templates").json()["items"][0]
    room: JsonObject = create_room(auth_client, alice, template_id)

    assert card["owner_name"] == "TierList"
    assert room["code"]
    assert logged_actions(db_session, template_id) == [
        ModerationActionKind.CREATE,
        ModerationActionKind.PUBLISH,
    ]


def test_publishing_needs_tiles(auth_client: TestClient, nina: dict[str, str]):
    template_id: str = create_official(auth_client, nina)

    response: Response = auth_client.post(
        f"/moderation/official-templates/{template_id}/publish", headers=nina
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HAS_NO_TILES


def test_only_a_published_official_template_can_be_featured(
    auth_client: TestClient, nina: dict[str, str]
):
    template_id: str = create_official(auth_client, nina)

    response: Response = auth_client.post(
        f"/moderation/official-templates/{template_id}/feature", headers=nina
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_PUBLISHED


def test_the_featured_templates_come_most_recently_featured_first_and_leave_when_unpublished(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    first_id: str = published_official(auth_client, db_session, nina)
    second_id: str = published_official(auth_client, db_session, nina)
    for template_id in (first_id, second_id):
        assert (
            auth_client.post(
                f"/moderation/official-templates/{template_id}/feature", headers=nina
            ).status_code
            == 200
        )

    featured: list[JsonObject] = auth_client.get("/marketplace/featured").json()["items"]
    assert [item["id"] for item in featured] == [second_id, first_id]
    assert all(item["featured"] for item in featured)

    auth_client.post(f"/moderation/official-templates/{second_id}/unpublish", headers=nina)

    featured_ids: list[str] = [
        item["id"] for item in auth_client.get("/marketplace/featured").json()["items"]
    ]
    assert featured_ids == [first_id]
    assert stored_template(db_session, second_id).featured_at is None
    assert logged_actions(db_session, second_id)[-2:] == [
        ModerationActionKind.FEATURE,
        ModerationActionKind.UNPUBLISH,
    ]


def test_an_official_template_is_deleted_like_any_template(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = published_official(auth_client, db_session, nina)

    response: Response = auth_client.delete(
        f"/moderation/official-templates/{template_id}", headers=nina
    )

    assert response.status_code == 204
    assert stored_template(db_session, template_id).deleted_at is not None
    deleted: list[JsonObject] = auth_client.get(
        "/moderation/templates/deleted", headers=nina
    ).json()["templates"]
    assert [(item["id"], item["owner_name"]) for item in deleted] == [(template_id, "TierList")]
    assert logged_actions(db_session, template_id)[-1] == ModerationActionKind.DELETE


def test_banning_the_super_admin_who_created_it_changes_nothing(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = published_official(auth_client, db_session, nina)
    nina_account: User = db_session.scalars(select(User).where(User.email == NINA_EMAIL)).one()
    nina_account.role = nina_account.role.USER
    db_session.flush()
    ban_account(db_session, NINA_EMAIL)

    assert template_id in [
        item["id"] for item in auth_client.get("/marketplace/templates").json()["items"]
    ]


def test_the_official_account_cannot_be_banned_nor_found(
    auth_client: TestClient, nina: dict[str, str]
):
    ban: Response = auth_client.post(
        f"/moderation/accounts/{OFFICIAL_ACCOUNT_ID}/ban",
        json={"reason": "Spam", "ends_at": None},
        headers=nina,
    )
    search: JsonObject = auth_client.get(
        "/moderation/accounts", params={"query": "tierlist"}, headers=nina
    ).json()

    assert ban.status_code == 409
    assert ban.json()["code"] == ErrorCode.CANNOT_BAN_SUPER_ADMIN
    assert search["accounts"] == []


def test_hiding_a_featured_official_template_takes_it_out_of_the_picks(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    template_id: str = published_official(auth_client, db_session, nina)
    auth_client.post(f"/moderation/official-templates/{template_id}/feature", headers=nina)

    response: Response = auth_client.post(
        f"/moderation/templates/{template_id}/hide", json={"reason": "Spam"}, headers=nina
    )

    assert response.status_code == 204
    assert stored_template(db_session, template_id).featured_at is None


def test_no_password_reset_can_be_asked_for_the_official_account(
    auth_client: TestClient, sent_emails: list[Email]
):
    response: Response = auth_client.post(
        "/auth/password/forgot", json={"email": "official@tierlist.invalid"}
    )

    assert response.status_code == 422
    assert sent_emails == []
