import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.templates import (
    DEFAULT_TIERS,
    FREE_PLAN_MAX_TILES,
    NEW_TIER_COLOR,
    NEW_TIER_NAME,
    TEMPLATE_NAME_MAX_LENGTH,
    TIER_NAME_MAX_LENGTH,
    TILE_TEXT_MAX_LENGTH,
)
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
    """Ajoute des tuiles directement en base : plus rapide que l'API quand un test a besoin de
    beaucoup de tuiles (ex. atteindre la limite)."""
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
    assert body["max_tiles"] == FREE_PLAN_MAX_TILES
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

    tier_url = f"{url}/tiers/{template['tiers'][0]['id']}"
    tile_url = f"{url}/tiles/{add_tile(auth_client, alice, template['id'], 'Pizza')['id']}"
    template = auth_client.get(url, headers=alice).json()

    responses = [
        auth_client.get(url, headers=bob),
        auth_client.patch(url, json={"name": "Stolen"}, headers=bob),
        auth_client.delete(url, headers=bob),
        auth_client.post(f"{url}/tiers", headers=bob),
        auth_client.patch(tier_url, json={"name": "Stolen"}, headers=bob),
        auth_client.delete(tier_url, headers=bob),
        auth_client.post(f"{url}/tiles", json={"text": "Stolen"}, headers=bob),
        auth_client.patch(tile_url, json={"text": "Stolen"}, headers=bob),
        auth_client.delete(tile_url, headers=bob),
    ]

    for response in responses:
        assert response.status_code == 404
        assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND
    # Le template d'Alice n'a pas changé
    unchanged = auth_client.get(url, headers=alice).json()
    assert unchanged["name"] == "Alice's template"
    assert unchanged["tiers"] == template["tiers"]
    assert unchanged["tiles"] == template["tiles"]


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
        ("POST", f"/templates/{uuid.uuid4()}/tiers"),
        ("PATCH", f"/templates/{uuid.uuid4()}/tiers/{uuid.uuid4()}"),
        ("DELETE", f"/templates/{uuid.uuid4()}/tiers/{uuid.uuid4()}"),
        ("POST", f"/templates/{uuid.uuid4()}/tiles"),
        ("PATCH", f"/templates/{uuid.uuid4()}/tiles/{uuid.uuid4()}"),
        ("DELETE", f"/templates/{uuid.uuid4()}/tiles/{uuid.uuid4()}"),
    ],
)
def test_template_routes_require_authentication(auth_client: TestClient, method: str, path: str):
    response = auth_client.request(method, path, json={"name": "Movies", "text": "Pizza"})

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


# --- Tiers ---------------------------------------------------------------------------------


def tier_names(template: dict) -> list[str]:
    return [tier["name"] for tier in template["tiers"]]


def tier_positions(template: dict) -> list[int]:
    return [tier["position"] for tier in template["tiers"]]


def tier_id(template: dict, name: str) -> str:
    for tier in template["tiers"]:
        if tier["name"] == name:
            return tier["id"]
    raise AssertionError(f"Tier {name} absent")


def test_add_tier_at_the_bottom_with_the_default_name_and_color(
    auth_client: TestClient, alice: dict[str, str]
):
    template = create_template(auth_client, alice, "Movies")

    response = auth_client.post(f"/templates/{template['id']}/tiers", headers=alice)

    assert response.status_code == 201
    body = response.json()
    assert tier_names(body) == ["S", "A", "B", "C", "D", "E", NEW_TIER_NAME]
    assert body["tiers"][-1]["color"] == NEW_TIER_COLOR
    assert tier_positions(body) == list(range(len(DEFAULT_TIERS) + 1))
    assert body["updated_at"] > template["updated_at"]


def test_rename_and_recolor_a_tier(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Movies")
    url = f"/templates/{template['id']}/tiers/{tier_id(template, 'S')}"

    response = auth_client.patch(
        url, json={"name": "  Masterpiece  ", "color": "#a1b2c3"}, headers=alice
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tiers"][0]["name"] == "Masterpiece"
    # Enregistrée en majuscules
    assert body["tiers"][0]["color"] == "#A1B2C3"
    assert tier_names(body)[1:] == ["A", "B", "C", "D", "E"]
    assert body["updated_at"] > template["updated_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * (TIER_NAME_MAX_LENGTH + 1)},
        {"color": "red"},
        {"color": "#12345"},
        {"color": "#GGGGGG"},
        {"position": -1},
    ],
)
def test_update_tier_validates_the_fields(
    auth_client: TestClient, alice: dict[str, str], payload: dict
):
    template = create_template(auth_client, alice, "Movies")
    url = f"/templates/{template['id']}/tiers/{tier_id(template, 'S')}"

    response = auth_client.patch(url, json=payload, headers=alice)

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.VALIDATION_ERROR
    unchanged = auth_client.get(f"/templates/{template['id']}", headers=alice).json()
    assert unchanged["tiers"] == template["tiers"]


@pytest.mark.parametrize(
    ("name", "position", "expected_names"),
    [
        # Vers le bas
        ("S", 2, ["A", "B", "S", "C", "D", "E"]),
        # Vers le haut
        ("D", 0, ["D", "S", "A", "B", "C", "E"]),
        # Au-delà de la fin : en dernier
        ("B", 99, ["S", "A", "C", "D", "E", "B"]),
        # Sur place
        ("C", 3, ["S", "A", "B", "C", "D", "E"]),
    ],
)
def test_move_a_tier_keeps_the_positions_continuous(
    auth_client: TestClient,
    alice: dict[str, str],
    name: str,
    position: int,
    expected_names: list[str],
):
    template = create_template(auth_client, alice, "Movies")
    url = f"/templates/{template['id']}/tiers/{tier_id(template, name)}"

    response = auth_client.patch(url, json={"position": position}, headers=alice)

    assert response.status_code == 200
    assert tier_names(response.json()) == expected_names
    assert tier_positions(response.json()) == list(range(len(DEFAULT_TIERS)))
    # Relu depuis la base : l'ordre est bien enregistré
    stored = auth_client.get(f"/templates/{template['id']}", headers=alice).json()
    assert tier_names(stored) == expected_names


def test_delete_a_tier_renumbers_the_others(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    template = create_template(auth_client, alice, "Movies")
    url = f"/templates/{template['id']}/tiers/{tier_id(template, 'B')}"

    response = auth_client.delete(url, headers=alice)

    assert response.status_code == 200
    body = response.json()
    assert tier_names(body) == ["S", "A", "C", "D", "E"]
    assert tier_positions(body) == [0, 1, 2, 3, 4]
    assert body["updated_at"] > template["updated_at"]
    assert len(db_session.scalars(select(Tier)).all()) == len(DEFAULT_TIERS) - 1


def test_the_last_tier_cannot_be_deleted(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Movies")
    for name in ["S", "A", "B", "C", "D"]:
        auth_client.delete(
            f"/templates/{template['id']}/tiers/{tier_id(template, name)}", headers=alice
        )

    response = auth_client.delete(
        f"/templates/{template['id']}/tiers/{tier_id(template, 'E')}", headers=alice
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.LAST_TIER
    remaining = auth_client.get(f"/templates/{template['id']}", headers=alice).json()
    assert tier_names(remaining) == ["E"]


def test_unknown_tier_is_not_found(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Movies")
    other = create_template(auth_client, alice, "Books")
    # Un tier inconnu, puis un tier d'un autre template du même utilisateur
    for unknown_tier_id in (str(uuid.uuid4()), tier_id(other, "S")):
        url = f"/templates/{template['id']}/tiers/{unknown_tier_id}"
        for response in (
            auth_client.patch(url, json={"name": "New name"}, headers=alice),
            auth_client.delete(url, headers=alice),
        ):
            assert response.status_code == 404
            assert response.json()["code"] == ErrorCode.TIER_NOT_FOUND


# --- Tuiles --------------------------------------------------------------------------------


def add_tile(client: TestClient, headers: dict[str, str], template_id: str, text: str) -> dict:
    """Ajoute une tuile par l'API et renvoie la tuile créée (la dernière)."""
    response = client.post(f"/templates/{template_id}/tiles", json={"text": text}, headers=headers)
    assert response.status_code == 201
    return response.json()["tiles"][-1]


def tile_texts(template: dict) -> list[str]:
    return [tile["text"] for tile in template["tiles"]]


def tile_positions(template: dict) -> list[int]:
    return [tile["position"] for tile in template["tiles"]]


def test_add_text_tiles_at_the_end(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Food")
    add_tile(auth_client, alice, template["id"], "Pizza")

    response = auth_client.post(
        f"/templates/{template['id']}/tiles", json={"text": "  Sushi  "}, headers=alice
    )

    assert response.status_code == 201
    body = response.json()
    assert tile_texts(body) == ["Pizza", "Sushi"]
    assert tile_positions(body) == [0, 1]
    assert body["updated_at"] > template["updated_at"]


@pytest.mark.parametrize("text", ["", "   ", "x" * (TILE_TEXT_MAX_LENGTH + 1)])
def test_add_tile_validates_the_text(auth_client: TestClient, alice: dict[str, str], text: str):
    template = create_template(auth_client, alice, "Food")

    response = auth_client.post(
        f"/templates/{template['id']}/tiles", json={"text": text}, headers=alice
    )

    # Sans image (pas encore gérée), une tuile sans texte n'aurait aucun contenu
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [error["field"] for error in errors] == ["body.text"]
    assert auth_client.get(f"/templates/{template['id']}", headers=alice).json()["tiles"] == []


def test_the_tile_limit_is_refused_with_the_limit(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    template = create_template(auth_client, alice, "Food")
    add_tiles(db_session, template["id"], FREE_PLAN_MAX_TILES)

    response = auth_client.post(
        f"/templates/{template['id']}/tiles", json={"text": "One too many"}, headers=alice
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == ErrorCode.TILE_LIMIT_REACHED
    assert body["params"] == {"max_tiles": FREE_PLAN_MAX_TILES}
    assert len(db_session.scalars(select(Tile)).all()) == FREE_PLAN_MAX_TILES


def test_edit_a_tile_text(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Food")
    tile = add_tile(auth_client, alice, template["id"], "Piza")
    url = f"/templates/{template['id']}/tiles/{tile['id']}"

    response = auth_client.patch(url, json={"text": " Pizza "}, headers=alice)

    assert response.status_code == 200
    assert tile_texts(response.json()) == ["Pizza"]


@pytest.mark.parametrize(
    "payload",
    [{"text": ""}, {"text": "   "}, {"text": "x" * (TILE_TEXT_MAX_LENGTH + 1)}, {"position": -1}],
)
def test_update_tile_validates_the_fields(
    auth_client: TestClient, alice: dict[str, str], payload: dict
):
    template = create_template(auth_client, alice, "Food")
    tile = add_tile(auth_client, alice, template["id"], "Pizza")
    url = f"/templates/{template['id']}/tiles/{tile['id']}"

    response = auth_client.patch(url, json=payload, headers=alice)

    assert response.status_code == 422
    assert tile_texts(auth_client.get(f"/templates/{template['id']}", headers=alice).json()) == [
        "Pizza"
    ]


@pytest.mark.parametrize(
    ("text", "position", "expected_texts"),
    [
        ("Pizza", 2, ["Sushi", "Tacos", "Pizza"]),
        ("Tacos", 0, ["Tacos", "Pizza", "Sushi"]),
        ("Sushi", 99, ["Pizza", "Tacos", "Sushi"]),
    ],
)
def test_move_a_tile_keeps_the_positions_continuous(
    auth_client: TestClient,
    alice: dict[str, str],
    text: str,
    position: int,
    expected_texts: list[str],
):
    template = create_template(auth_client, alice, "Food")
    tile_ids: dict[str, str] = {}
    for name in ("Pizza", "Sushi", "Tacos"):
        tile_ids[name] = add_tile(auth_client, alice, template["id"], name)["id"]
    url = f"/templates/{template['id']}/tiles/{tile_ids[text]}"

    response = auth_client.patch(url, json={"position": position}, headers=alice)

    assert response.status_code == 200
    assert tile_texts(response.json()) == expected_texts
    assert tile_positions(response.json()) == [0, 1, 2]
    stored = auth_client.get(f"/templates/{template['id']}", headers=alice).json()
    assert tile_texts(stored) == expected_texts


def test_delete_a_tile_renumbers_the_others(
    auth_client: TestClient, alice: dict[str, str], db_session: Session
):
    template = create_template(auth_client, alice, "Food")
    add_tile(auth_client, alice, template["id"], "Pizza")
    sushi = add_tile(auth_client, alice, template["id"], "Sushi")
    add_tile(auth_client, alice, template["id"], "Tacos")

    response = auth_client.delete(f"/templates/{template['id']}/tiles/{sushi['id']}", headers=alice)

    assert response.status_code == 200
    body = response.json()
    assert tile_texts(body) == ["Pizza", "Tacos"]
    assert tile_positions(body) == [0, 1]
    assert body["updated_at"] > template["updated_at"]
    assert len(db_session.scalars(select(Tile)).all()) == 2


def test_unknown_tile_is_not_found(auth_client: TestClient, alice: dict[str, str]):
    template = create_template(auth_client, alice, "Food")
    other = create_template(auth_client, alice, "Drinks")
    other_tile = add_tile(auth_client, alice, other["id"], "Water")
    # Une tuile inconnue, puis une tuile d'un autre template du même utilisateur
    for unknown_tile_id in (str(uuid.uuid4()), other_tile["id"]):
        url = f"/templates/{template['id']}/tiles/{unknown_tile_id}"
        for response in (
            auth_client.patch(url, json={"text": "New text"}, headers=alice),
            auth_client.delete(url, headers=alice),
        ):
            assert response.status_code == 404
            assert response.json()["code"] == ErrorCode.TILE_NOT_FOUND
