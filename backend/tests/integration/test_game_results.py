"""Résultats d'une partie close (US-5.2), lus par son lien (US-5.3) : classement de chaque joueur,
vue globale avec les absents, classement médian, avec ou sans les votes absents."""

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    create_room,
    create_template,
    next_item,
    place,
    place_current_in_first_tier,
    play_and_close,
    register,
    start_game,
)

pytestmark = pytest.mark.integration

TILE_COUNT = 3


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def alice_room(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
) -> JsonObject:
    """Salle d'Alice (3 tuiles texte), que Bob a rejointe."""
    template_id: str = create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)
    room: JsonObject = create_room(auth_client, alice, template_id)
    assert auth_client.post(f"/rooms/{room['code']}/join", headers=bob).status_code == 200
    return room


@pytest.fixture
def public_token(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
) -> str:
    """Alice, Bob et l'invitée Lou jouent :
    - Tile 0 : Alice en S, Bob en A, Lou absente ;
    - Tile 1 : Alice en tête de S ; Bob absent, il la rattrape en B pendant le cooldown ; Lou
      absente ;
    - Tile 2 : personne.
    Renvoie le jeton du lien de résultats, lu dans le lobby."""
    code: str = alice_room["code"]
    assert auth_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"}).status_code == 201
    first: JsonObject = start_game(auth_client, code, alice)
    tiers: list[JsonObject] = first["game"]["tiers"]
    place_current_in_first_tier(auth_client, first, alice)
    bob_place: Response = place(
        auth_client, code, first["game"]["current_item"]["id"], tiers[1]["id"], 0, bob
    )
    assert bob_place.status_code == 200
    second: JsonObject = next_item(auth_client, code, alice)
    tile_1_id: str = second["game"]["current_item"]["id"]
    place_current_in_first_tier(auth_client, second, alice)
    next_item(auth_client, code, alice)
    next_item(auth_client, code, alice)
    caught_up: Response = place(auth_client, code, tile_1_id, tiers[2]["id"], 0, bob)
    assert caught_up.status_code == 200
    closed: JsonObject = play_and_close(auth_client, code, alice)
    return closed["past_games"][0]["public_token"]


def results(client: TestClient, token: str, include_absent_votes: bool = True) -> Response:
    # Sans en-tête ni cookie de compte : le lien suffit
    return client.get(
        f"/results/{token}", params={"include_absent_votes": str(include_absent_votes).lower()}
    )


def names(body: JsonObject) -> tuple[dict[str, str], dict[str, str]]:
    """(nom de tier par id, texte d'item par id) de la réponse."""
    tier_names: dict[str, str] = {tier["id"]: tier["name"] for tier in body["tiers"]}
    item_texts: dict[str, str] = {item["id"]: item["text"] for item in body["items"]}
    return tier_names, item_texts


def distribution(body: JsonObject) -> dict[str, tuple[list[int], int, str | None]]:
    """Par texte d'item : (votes par tier, absents, tier médian)."""
    tier_names, item_texts = names(body)
    return {
        item_texts[entry["item_id"]]: (
            entry["votes_per_tier"],
            entry["absent_count"],
            tier_names.get(entry["median_tier_id"]) if entry["median_tier_id"] else None,
        )
        for entry in body["distribution"]
    }


def boards(body: JsonObject) -> dict[str, tuple[dict[str, list[str]], list[str]]]:
    """Par joueur : (items par nom de tier, sans les tiers vides ; items jamais placés)."""
    tier_names, item_texts = names(body)
    return {
        player["display_name"]: (
            {
                tier_names[tier["tier_id"]]: [item_texts[item_id] for item_id in tier["item_ids"]]
                for tier in player["tiers"]
                if tier["item_ids"]
            },
            [item_texts[item_id] for item_id in player["unplaced_item_ids"]],
        )
        for player in body["players"]
    }


def test_the_results_show_every_ranking_the_distribution_and_the_median(
    auth_client: TestClient, public_token: str
):
    response: Response = results(auth_client, public_token)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["template_name"] == "Food"
    assert body["include_absent_votes"] is True
    assert [tier["name"] for tier in body["tiers"]] == ["S", "A", "B", "C", "D", "E"]
    assert [item["text"] for item in body["items"]] == ["Tile 0", "Tile 1", "Tile 2"]
    assert boards(body) == {
        "alice": ({"S": ["Tile 1", "Tile 0"]}, ["Tile 2"]),
        "bob": ({"A": ["Tile 0"], "B": ["Tile 1"]}, ["Tile 2"]),
        "Lou": ({}, ["Tile 0", "Tile 1", "Tile 2"]),
    }
    assert distribution(body) == {
        # Médian : le moins bon des deux votes du milieu (results.md §2.3)
        "Tile 0": ([1, 1, 0, 0, 0, 0], 1, "A"),
        "Tile 1": ([1, 0, 1, 0, 0, 0], 1, "B"),
        "Tile 2": ([0, 0, 0, 0, 0, 0], 3, None),
    }
    _, item_texts = names(body)
    median: dict[str, list[str]] = {
        tier["tier_id"]: [item_texts[item_id] for item_id in tier["item_ids"]]
        for tier in body["median_ranking"]
    }
    tier_ids: dict[str, str] = {tier["name"]: tier["id"] for tier in body["tiers"]}
    assert median[tier_ids["A"]] == ["Tile 0"]
    assert median[tier_ids["B"]] == ["Tile 1"]
    assert [item_texts[item_id] for item_id in body["unranked_item_ids"]] == ["Tile 2"]


def test_without_absent_votes_the_caught_up_votes_and_the_absents_are_ignored(
    auth_client: TestClient, public_token: str
):
    response: Response = results(auth_client, public_token, include_absent_votes=False)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["include_absent_votes"] is False
    # Le rattrapage de Bob ne compte plus, et la colonne des absents est vide (results.md §2.1)
    assert distribution(body) == {
        "Tile 0": ([1, 1, 0, 0, 0, 0], 0, "A"),
        "Tile 1": ([1, 0, 0, 0, 0, 0], 0, "S"),
        "Tile 2": ([0, 0, 0, 0, 0, 0], 0, None),
    }
    # Les classements des joueurs ne changent pas
    assert boards(body)["bob"] == ({"A": ["Tile 0"], "B": ["Tile 1"]}, ["Tile 2"])


def test_the_room_admin_who_does_not_play_is_not_in_the_results(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    auth_client.patch(f"/rooms/{code}/settings", json={"admin_plays": False}, headers=alice)
    started: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, started, bob)
    token: str = play_and_close(auth_client, code, alice)["past_games"][0]["public_token"]

    body: JsonObject = results(auth_client, token).json()

    assert [player["display_name"] for player in body["players"]] == ["bob"]
    assert distribution(body)["Tile 0"] == ([1, 0, 0, 0, 0, 0], 0, "S")


def test_an_unknown_results_link_is_not_found(auth_client: TestClient):
    response: Response = results(auth_client, "unknown-token")

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.RESULTS_NOT_FOUND


def test_the_lobby_lists_the_past_games_of_the_room(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject, public_token: str
):
    room: JsonObject = auth_client.get(f"/rooms/{alice_room['code']}", headers=bob).json()

    assert room["game"] is None
    assert len(room["past_games"]) == 1
    past_game: JsonObject = room["past_games"][0]
    assert past_game["public_token"] == public_token
    assert past_game["player_count"] == 3
    assert past_game["closed_at"] is not None


def test_the_results_link_keeps_working_after_the_room_is_closed(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject, public_token: str
):
    closed: Response = auth_client.delete(f"/rooms/{alice_room['code']}", headers=alice)
    assert closed.status_code == 204

    response: Response = results(auth_client, public_token)

    # US-5.3 : la partie survit à sa salle, son lien aussi
    assert response.status_code == 200
    assert sorted(boards(response.json())) == ["Lou", "alice", "bob"]


def test_the_results_link_keeps_a_player_who_deleted_their_account(
    auth_client: TestClient, bob: dict[str, str], public_token: str
):
    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=bob
    )
    assert deleted.status_code == 204

    response: Response = results(auth_client, public_token)

    assert response.status_code == 200
    assert boards(response.json())["bob"] == ({"A": ["Tile 0"], "B": ["Tile 1"]}, ["Tile 2"])
