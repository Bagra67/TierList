import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.templates import DEFAULT_TIERS, TEMPLATE_NAME_MAX_LENGTH
from app.models.template import Template
from app.models.tier import Tier
from app.models.tile import Tile
from app.models.user import User

# Tous les tests de ce fichier ont besoin d'un vrai PostgreSQL : `pytest -m "not integration"`
# les saute (marqueur déclaré dans pyproject.toml)
pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"


def register(client: TestClient, email: str) -> dict[str, str]:
    """Crée un compte et renvoie l'en-tête Authorization de son access token."""
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


def create_template(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post("/templates", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def add_tiles(db_session: Session, template_id: str, count: int) -> None:
    """Ajoute des tuiles directement en base : l'API des tuiles n'existe pas encore."""
    for position in range(count):
        db_session.add(
            Tile(template_id=uuid.UUID(template_id), text=f"Tile {position}", position=position)
        )
    db_session.flush()


def test_create_template_with_the_default_tiers(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    response = auth_client.post("/templates", json={"name": "  Video games  "}, headers=alice)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Video games"
    tiers = [(tier["name"], tier["color"], tier["position"]) for tier in body["tiers"]]
    expected_tiers = [
        (name, color, position) for position, (name, color) in enumerate(DEFAULT_TIERS)
    ]
    assert tiers == expected_tiers
    assert body["tiles"] == []
    template = db_session.scalars(select(Template)).one()
    alice_user = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    assert template.owner_id == alice_user.id
    assert template.deleted_at is None


@pytest.mark.parametrize("name", ["", "   ", "x" * (TEMPLATE_NAME_MAX_LENGTH + 1)])
def test_create_template_validates_the_name(
    auth_client: TestClient, alice: dict[str, str], db_session: Session, name: str
):
    response = auth_client.post("/templates", json={"name": name}, headers=alice)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["errors"]] == ["body.name"]
    assert db_session.scalars(select(Template)).all() == []


def test_list_is_empty_when_the_user_has_no_template(
    auth_client: TestClient, alice: dict[str, str]
):
    response = auth_client.get("/templates", headers=alice)

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_shows_only_my_templates_with_their_tile_count(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], db_session: Session
):
    movies = create_template(auth_client, alice, "Movies")
    create_template(auth_client, alice, "Games")
    create_template(auth_client, bob, "Bob's template")
    add_tiles(db_session, movies["id"], 3)

    response = auth_client.get("/templates", headers=alice)

    assert response.status_code == 200
    items = response.json()["items"]
    tile_count_by_name = {item["name"]: item["tile_count"] for item in items}
    assert tile_count_by_name == {"Movies": 3, "Games": 0}


def test_list_shows_the_last_modified_template_first(
    auth_client: TestClient, alice: dict[str, str]
):
    first = create_template(auth_client, alice, "First")
    create_template(auth_client, alice, "Second")
    auth_client.patch(f"/templates/{first['id']}", json={"name": "First, renamed"}, headers=alice)

    response = auth_client.get("/templates", headers=alice)

    assert [item["name"] for item in response.json()["items"]] == ["First, renamed", "Second"]


def test_get_template_returns_its_tiers_and_tiles(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    template = create_template(auth_client, alice, "Movies")
    add_tiles(db_session, template["id"], 2)

    response = auth_client.get(f"/templates/{template['id']}", headers=alice)

    assert response.status_code == 200
    body = response.json()
    assert len(body["tiers"]) == len(DEFAULT_TIERS)
    assert [tile["text"] for tile in body["tiles"]] == ["Tile 0", "Tile 1"]


def test_rename_template_updates_the_last_modification_date(
    auth_client: TestClient, alice: dict[str, str]
):
    template = create_template(auth_client, alice, "Movies")

    response = auth_client.patch(
        f"/templates/{template['id']}", json={"name": "Films"}, headers=alice
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Films"
    assert response.json()["updated_at"] > template["updated_at"]


def test_delete_template_is_a_soft_delete(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    template = create_template(auth_client, alice, "Movies")

    response = auth_client.delete(f"/templates/{template['id']}", headers=alice)

    assert response.status_code == 204
    assert auth_client.get("/templates", headers=alice).json() == {"items": []}
    assert auth_client.get(f"/templates/{template['id']}", headers=alice).status_code == 404
    # Toujours en base, avec ses tiers, jusqu'à la purge
    stored = db_session.scalars(select(Template)).one()
    assert stored.deleted_at is not None
    assert len(db_session.scalars(select(Tier)).all()) == len(DEFAULT_TIERS)


def test_templates_of_other_users_are_not_found(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    template = create_template(auth_client, alice, "Alice's template")
    url = f"/templates/{template['id']}"

    responses = [
        auth_client.get(url, headers=bob),
        auth_client.patch(url, json={"name": "Stolen"}, headers=bob),
        auth_client.delete(url, headers=bob),
    ]

    for response in responses:
        assert response.status_code == 404
        assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND
    # Le template d'Alice n'a pas changé
    assert auth_client.get(url, headers=alice).json()["name"] == "Alice's template"


def test_unknown_or_deleted_template_is_not_found(auth_client: TestClient, alice: dict[str, str]):
    deleted = create_template(auth_client, alice, "Deleted")
    auth_client.delete(f"/templates/{deleted['id']}", headers=alice)

    for template_id in (deleted["id"], str(uuid.uuid4())):
        url = f"/templates/{template_id}"
        for response in (
            auth_client.get(url, headers=alice),
            auth_client.patch(url, json={"name": "New name"}, headers=alice),
            auth_client.delete(url, headers=alice),
        ):
            assert response.status_code == 404
            assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/templates"),
        ("GET", "/templates"),
        ("GET", f"/templates/{uuid.uuid4()}"),
        ("PATCH", f"/templates/{uuid.uuid4()}"),
        ("DELETE", f"/templates/{uuid.uuid4()}"),
    ],
)
def test_template_routes_require_authentication(auth_client: TestClient, method: str, path: str):
    response = auth_client.request(method, path, json={"name": "Movies"})

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.NOT_AUTHENTICATED


def test_deleting_the_account_deletes_its_templates(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    create_template(auth_client, alice, "Movies")

    response = auth_client.request("DELETE", "/auth/me", json={"password": PASSWORD}, headers=alice)

    assert response.status_code == 204
    assert db_session.scalars(select(Template)).all() == []
    assert db_session.scalars(select(Tier)).all() == []
