import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import TemplateModeration
from app.models.template import Template
from app.models.user import User
from tests.integration.helpers import (
    JsonObject,
    create_template,
    register,
    register_super_admin,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL: str = "alice@example.com"


def confirm_email(db_session: Session, email: str) -> None:
    user: User = db_session.scalars(select(User).where(User.email == email)).one()
    user.email_verified_at = datetime.now(UTC)
    db_session.flush()


@pytest.fixture
def alice(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    headers: dict[str, str] = register(auth_client, ALICE_EMAIL)
    confirm_email(db_session, ALICE_EMAIL)
    return headers


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice)


def set_visibility(
    client: TestClient, headers: dict[str, str], template_id: str, visibility: str
) -> Response:
    return client.put(
        f"/templates/{template_id}/visibility", json={"visibility": visibility}, headers=headers
    )


def stored_template(db_session: Session, template_id: str) -> Template:
    db_session.expire_all()
    template: Template | None = db_session.get(Template, uuid.UUID(template_id))
    assert template is not None
    return template


def set_hidden(db_session: Session, template_id: str) -> None:
    template: Template = stored_template(db_session, template_id)
    template.moderation = TemplateModeration.HIDDEN
    template.moderation_reason = "Harassment"
    db_session.flush()


def test_a_new_template_is_private(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    template: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()

    assert template["visibility"] == "private"
    assert template["first_made_public_at"] is None


def test_the_owner_with_a_confirmed_email_makes_a_template_public(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    response: Response = set_visibility(auth_client, alice, template_id, "public")

    assert response.status_code == 200
    assert response.json()["visibility"] == "public"
    assert response.json()["first_made_public_at"] is not None
    summary: JsonObject = auth_client.get("/templates", headers=alice).json()["items"][0]
    assert summary["visibility"] == "public"
    assert summary["first_made_public_at"] == response.json()["first_made_public_at"]


def test_the_date_first_made_public_is_kept_when_the_template_is_made_public_again(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    first_date: str = set_visibility(auth_client, alice, template_id, "public").json()[
        "first_made_public_at"
    ]

    private: Response = set_visibility(auth_client, alice, template_id, "private")
    public_again: Response = set_visibility(auth_client, alice, template_id, "public")

    assert private.json()["visibility"] == "private"
    assert private.json()["first_made_public_at"] == first_date
    assert public_again.json()["first_made_public_at"] == first_date


def test_setting_the_same_visibility_again_changes_nothing(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    first: JsonObject = set_visibility(auth_client, alice, template_id, "public").json()

    second: Response = set_visibility(auth_client, alice, template_id, "public")

    assert second.status_code == 200
    assert second.json()["visibility"] == "public"
    assert second.json()["first_made_public_at"] == first["first_made_public_at"]


def test_an_unconfirmed_email_cannot_make_a_template_public(
    auth_client: TestClient, db_session: Session
) -> None:
    bob: dict[str, str] = register(auth_client, "bob@example.com")
    template_id: str = create_template(auth_client, db_session, bob)

    response: Response = set_visibility(auth_client, bob, template_id, "public")

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.EMAIL_NOT_VERIFIED
    assert stored_template(db_session, template_id).visibility == "private"


def test_a_hidden_template_cannot_be_made_public(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    set_hidden(db_session, template_id)

    response: Response = set_visibility(auth_client, alice, template_id, "public")

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HIDDEN
    assert stored_template(db_session, template_id).visibility == "private"


def test_a_template_without_tiles_cannot_be_made_public(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
) -> None:
    template_id: str = create_template(auth_client, db_session, alice, tile_count=0)

    response: Response = set_visibility(auth_client, alice, template_id, "public")

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HAS_NO_TILES
    assert stored_template(db_session, template_id).first_made_public_at is None


def test_a_hidden_public_template_can_go_back_to_private(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    set_visibility(auth_client, alice, template_id, "public")
    set_hidden(db_session, template_id)

    response: Response = set_visibility(auth_client, alice, template_id, "private")

    assert response.status_code == 200
    assert response.json()["visibility"] == "private"


def test_hiding_then_unhiding_a_template_gives_back_the_visibility_chosen_by_its_owner(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    nina: dict[str, str] = register_super_admin(auth_client, db_session, "nina@example.com")
    set_visibility(auth_client, alice, template_id, "public")

    for action in ("hide", "unhide"):
        response: Response = auth_client.post(
            f"/moderation/templates/{template_id}/{action}",
            json={"reason": "Harassment"},
            headers=nina,
        )
        assert response.status_code == 204

    template: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()
    assert template["moderation"] == "none"
    assert template["visibility"] == "public"


def test_only_the_owner_can_change_the_visibility(
    auth_client: TestClient, db_session: Session, template_id: str
) -> None:
    carol: dict[str, str] = register(auth_client, "carol@example.com")
    confirm_email(db_session, "carol@example.com")

    response: Response = set_visibility(auth_client, carol, template_id, "public")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND
    assert stored_template(db_session, template_id).visibility == "private"


def test_a_deleted_template_cannot_change_its_visibility(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    assert auth_client.delete(f"/templates/{template_id}", headers=alice).status_code == 204

    response: Response = set_visibility(auth_client, alice, template_id, "public")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_changing_the_visibility_needs_a_session(auth_client: TestClient, template_id: str) -> None:
    response: Response = auth_client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}
    )

    assert response.status_code == 401


def test_an_unknown_visibility_is_refused(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    response: Response = set_visibility(auth_client, alice, template_id, "friends")

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_ERROR
