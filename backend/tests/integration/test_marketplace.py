from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.marketplace import MARKETPLACE_PAGE_SIZE
from app.constants.templates import DEFAULT_TIERS
from app.models.image import ImageStatus
from app.models.template import Template
from tests.integration.conftest import FAKE_IMAGE_BASE_URL
from tests.integration.helpers import (
    JsonObject,
    add_tile_with_image,
    ban_account,
    confirm_email,
    counted_queries,
    create_template,
    make_private,
    register,
    set_hidden,
    stored_template,
)

pytestmark = pytest.mark.integration

ALICE_EMAIL = "alice@example.com"
FIRST_PUBLICATION = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def alice(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    headers: dict[str, str] = register(auth_client, ALICE_EMAIL)
    confirm_email(db_session, ALICE_EMAIL)
    return headers


@pytest.fixture
def fans(auth_client: TestClient, db_session: Session) -> list[dict[str, str]]:
    emails: list[str] = [f"fan-{number}@example.com" for number in range(3)]
    headers: list[dict[str, str]] = [register(auth_client, email) for email in emails]
    for email in emails:
        confirm_email(db_session, email)
    return headers


def publish(
    client: TestClient,
    db_session: Session,
    owner: dict[str, str],
    name: str,
    tags: list[str] | None = None,
    days_after_first: int = 0,
    tile_count: int = 3,
) -> str:
    template_id: str = create_template(client, db_session, owner, tile_count)
    assert client.patch(f"/templates/{template_id}", json={"name": name}, headers=owner).is_success
    if tags:
        assert client.put(
            f"/templates/{template_id}/tags", json={"tags": tags}, headers=owner
        ).is_success
    make_public(client, db_session, template_id, owner, days_after_first)
    return template_id


def make_public(
    client: TestClient,
    db_session: Session,
    template_id: str,
    owner: dict[str, str],
    days_after_first: int = 0,
) -> None:
    assert client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}, headers=owner
    ).is_success
    template: Template = stored_template(db_session, template_id)
    template.first_made_public_at = FIRST_PUBLICATION + timedelta(days=days_after_first)
    db_session.flush()


def like(client: TestClient, template_id: str, fans: list[dict[str, str]], count: int) -> None:
    for fan in fans[:count]:
        assert client.put(f"/marketplace/templates/{template_id}/like", headers=fan).is_success


def marketplace(client: TestClient, **params: str | int) -> JsonObject:
    response: Response = client.get("/marketplace/templates", params=params)
    assert response.status_code == 200
    return response.json()


def names(page: JsonObject) -> list[str]:
    return [item["name"] for item in page["items"]]


def test_a_visitor_sees_the_cards_of_the_public_templates(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = publish(auth_client, db_session, alice, "Pokémon", ["Anime", "Jeux"])

    page: JsonObject = marketplace(auth_client)

    assert page == {
        "items": [
            {
                "id": template_id,
                "name": "Pokémon",
                "owner_name": "alice",
                "featured": False,
                "tags": ["Anime", "Jeux"],
                "tile_count": 3,
                "like_count": 0,
                "preview_image_url": None,
                "preview_image_removed": False,
                "tier_colors": [color for _, color in DEFAULT_TIERS],
                "copied_from": None,
            }
        ],
        "next_cursor": None,
    }


def test_the_templates_that_are_not_listed_never_appear(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    create_template(auth_client, db_session, alice)
    hidden_id: str = publish(auth_client, db_session, alice, "Hidden")
    set_hidden(db_session, hidden_id)
    private_id: str = publish(auth_client, db_session, alice, "Private again")
    make_private(auth_client, private_id, alice)
    publish(auth_client, db_session, alice, "Listed")

    assert names(marketplace(auth_client)) == ["Listed"]


def test_the_templates_of_a_banned_owner_never_appear(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    publish(auth_client, db_session, alice, "Food")
    ban_account(db_session, ALICE_EMAIL)

    assert marketplace(auth_client)["items"] == []


def test_the_most_liked_templates_come_first_then_the_newest(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], fans: list[dict[str, str]]
):
    old_and_liked: str = publish(auth_client, db_session, alice, "Old, liked", days_after_first=0)
    publish(auth_client, db_session, alice, "Old", days_after_first=1)
    publish(auth_client, db_session, alice, "New", days_after_first=2)
    like(auth_client, old_and_liked, fans, 2)

    page: JsonObject = marketplace(auth_client)

    assert names(page) == ["Old, liked", "New", "Old"]
    assert [item["like_count"] for item in page["items"]] == [2, 0, 0]


def test_the_newest_sort_follows_the_first_publication(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], fans: list[dict[str, str]]
):
    liked: str = publish(auth_client, db_session, alice, "Liked", days_after_first=0)
    publish(auth_client, db_session, alice, "Newest", days_after_first=1)
    like(auth_client, liked, fans, 3)

    assert names(marketplace(auth_client, sort="newest")) == ["Newest", "Liked"]


@pytest.mark.parametrize(
    ("search", "found"),
    [
        ("poke", ["Pokémon cards"]),
        ("POKÉ", ["Pokémon cards"]),
        ("kemon", []),
        ("poke cards", ["Pokémon cards"]),
        ("poke films", []),
        ("mario | zelda", ["Zelda", "Mario Kart"]),
        ("anim", ["Pokémon cards"]),
    ],
)
def test_the_keywords_match_the_start_of_the_words_of_the_name_and_tags(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    search: str,
    found: list[str],
):
    publish(auth_client, db_session, alice, "Pokémon cards", ["Anime"], days_after_first=0)
    publish(auth_client, db_session, alice, "Mario Kart", days_after_first=1)
    publish(auth_client, db_session, alice, "Zelda", days_after_first=2)

    assert names(marketplace(auth_client, q=search, sort="newest")) == found


def test_the_tag_filter_ignores_case_and_accents(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    publish(auth_client, db_session, alice, "Pokémon", ["Animé"])
    publish(auth_client, db_session, alice, "Mario")

    assert names(marketplace(auth_client, tag="anime")) == ["Pokémon"]


def test_the_marketplace_is_read_page_after_page_without_duplicates(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], fans: list[dict[str, str]]
):
    template_ids: list[str] = [
        publish(auth_client, db_session, alice, f"T{day}", days_after_first=day, tile_count=1)
        for day in range(MARKETPLACE_PAGE_SIZE + 2)
    ]
    like(auth_client, template_ids[0], fans, 1)

    first_page: JsonObject = marketplace(auth_client)
    second_page: JsonObject = marketplace(auth_client, cursor=first_page["next_cursor"])

    assert len(first_page["items"]) == MARKETPLACE_PAGE_SIZE
    assert second_page["next_cursor"] is None
    read: list[str] = [item["id"] for item in first_page["items"] + second_page["items"]]
    assert read[0] == template_ids[0]
    assert sorted(read) == sorted(template_ids)


def test_the_limit_reads_fewer_templates(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    for day in range(3):
        publish(auth_client, db_session, alice, f"Template {day}", days_after_first=day)

    page: JsonObject = marketplace(auth_client, limit=2)

    assert len(page["items"]) == 2
    assert page["next_cursor"] is not None


def test_a_cursor_made_for_another_sort_is_refused(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    for day in range(2):
        publish(auth_client, db_session, alice, f"Template {day}", days_after_first=day)
    cursor: str = marketplace(auth_client, limit=1)["next_cursor"]

    response: Response = auth_client.get(
        "/marketplace/templates", params={"cursor": cursor, "sort": "newest"}
    )

    assert response.status_code == 400
    assert response.json()["code"] == ErrorCode.INVALID_CURSOR


def test_more_than_eight_keywords_are_refused(auth_client: TestClient):
    response: Response = auth_client.get(
        "/marketplace/templates", params={"q": "a b c d e f g h i"}
    )

    assert response.status_code == 422


def test_the_preview_is_the_image_of_the_first_tile(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice, tile_count=0)
    _, first = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    add_tile_with_image(auth_client, db_session, alice, template_id, None)
    make_public(auth_client, db_session, template_id, alice)

    card: JsonObject = marketplace(auth_client)["items"][0]

    assert card["preview_image_url"] == f"{FAKE_IMAGE_BASE_URL}/{first.storage_key}"
    assert card["preview_image_removed"] is False


def test_a_removed_preview_image_is_not_served(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    template_id: str = create_template(auth_client, db_session, alice, tile_count=0)
    _, first = add_tile_with_image(auth_client, db_session, alice, template_id, None)
    make_public(auth_client, db_session, template_id, alice)
    first.status = ImageStatus.HIDDEN
    db_session.flush()

    card: JsonObject = marketplace(auth_client)["items"][0]

    assert card["preview_image_url"] is None
    assert card["preview_image_removed"] is True


def test_a_page_needs_the_same_queries_whatever_its_size(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    publish(auth_client, db_session, alice, "Alone", ["Solo"])
    with counted_queries(db_session) as one_template:
        marketplace(auth_client)
    for day in range(1, 5):
        publish(auth_client, db_session, alice, f"Template {day}", ["Tag"], days_after_first=day)
    with counted_queries(db_session) as five_templates:
        marketplace(auth_client)

    assert len(five_templates) == len(one_template)


def test_the_popular_tags_are_the_most_used_by_listed_templates(
    auth_client: TestClient, db_session: Session, alice: dict[str, str]
):
    publish(auth_client, db_session, alice, "One", ["Anime", "Jeux"])
    publish(auth_client, db_session, alice, "Two", ["animé"])
    hidden_id: str = publish(auth_client, db_session, alice, "Hidden", ["Films", "Musique"])
    set_hidden(db_session, hidden_id)

    response: Response = auth_client.get("/marketplace/tags")

    assert response.status_code == 200
    assert response.json() == {"tags": ["Anime", "Jeux"]}
