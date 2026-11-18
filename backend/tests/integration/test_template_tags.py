import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.template_tag import TemplateTag
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
    create_template,
    register,
    stored_template,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice)


def set_tags(
    client: TestClient, headers: dict[str, str], template_id: str, tags: list[str]
) -> Response:
    return client.put(f"/templates/{template_id}/tags", json={"tags": tags}, headers=headers)


def test_a_new_template_has_no_tags(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    template: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()

    assert template["tags"] == []


def test_the_owner_sets_tags_kept_in_their_order(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    before: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()

    response: Response = set_tags(auth_client, alice, template_id, ["  snacks ", "Soirée", "été"])

    assert response.status_code == 200
    assert response.json()["tags"] == ["snacks", "Soirée", "été"]
    assert response.json()["updated_at"] > before["updated_at"]
    reloaded: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()
    assert reloaded["tags"] == ["snacks", "Soirée", "été"]


def test_removing_and_adding_tags_replaces_the_list(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    set_tags(auth_client, alice, template_id, ["snacks", "party", "food"])

    response: Response = set_tags(auth_client, alice, template_id, ["food", "Snacks", "movies"])

    assert response.json()["tags"] == ["food", "Snacks", "movies"]


def test_a_tag_equal_to_an_earlier_one_ignoring_case_and_accents_is_dropped(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    response: Response = set_tags(
        auth_client, alice, template_id, ["Soirée", "soiree", "SOIRÉE", "jeux"]
    )

    assert response.status_code == 200
    assert response.json()["tags"] == ["Soirée", "jeux"]


def test_more_than_five_tags_are_refused(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    response: Response = set_tags(auth_client, alice, template_id, ["a", "b", "c", "d", "e", "f"])

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["errors"]] == ["body.tags"]


def test_a_tag_longer_than_thirty_characters_is_refused(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    response: Response = set_tags(auth_client, alice, template_id, ["a" * 31])

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["errors"]] == ["body.tags.0"]


def test_a_tag_without_latin_letter_or_digit_is_refused(
    auth_client: TestClient, alice: dict[str, str], template_id: str
) -> None:
    set_tags(auth_client, alice, template_id, ["snacks"])

    response: Response = set_tags(auth_client, alice, template_id, ["party", "!!!"])

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.INVALID_TAG
    kept: JsonObject = auth_client.get(f"/templates/{template_id}", headers=alice).json()
    assert kept["tags"] == ["snacks"]


def test_another_user_cannot_set_the_tags(auth_client: TestClient, template_id: str) -> None:
    bob: dict[str, str] = register(auth_client, "bob@example.com")

    response: Response = set_tags(auth_client, bob, template_id, ["snacks"])

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_the_search_text_follows_the_name_and_the_tags(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    assert stored_template(db_session, template_id).search_text == "food"

    auth_client.patch(f"/templates/{template_id}", json={"name": "Œufs & Crêpes"}, headers=alice)
    assert stored_template(db_session, template_id).search_text == "oeufs crepes"

    set_tags(auth_client, alice, template_id, ["Petit-déjeuner", "sucré"])
    assert stored_template(db_session, template_id).search_text == (
        "oeufs crepes petit dejeuner sucre"
    )

    set_tags(auth_client, alice, template_id, [])
    assert stored_template(db_session, template_id).search_text == "oeufs crepes"


def test_purging_a_template_deletes_its_tags(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    set_tags(auth_client, alice, template_id, ["snacks", "party"])

    db_session.delete(stored_template(db_session, template_id))
    db_session.flush()

    assert db_session.scalar(select(func.count()).select_from(TemplateTag)) == 0


def test_the_templates_list_shows_the_tags_without_a_query_per_template(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], template_id: str
) -> None:
    set_tags(auth_client, alice, template_id, ["snacks", "party"])
    with counted_queries(db_session) as one_template_statements:
        auth_client.get("/templates", headers=alice)
    other_template_id: str = create_template(auth_client, db_session, alice)
    set_tags(auth_client, alice, other_template_id, ["movies"])

    with counted_queries(db_session) as two_templates_statements:
        items: list[JsonObject] = auth_client.get("/templates", headers=alice).json()["items"]

    assert {item["id"]: item["tags"] for item in items} == {
        template_id: ["snacks", "party"],
        other_template_id: ["movies"],
    }
    assert len(two_templates_statements) == len(one_template_statements)
