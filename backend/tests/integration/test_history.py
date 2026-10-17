"""Historique d'un compte (US-5.5) : ses parties closes, jouées ou animées comme room admin, de
la plus récente à la plus ancienne, page par page."""

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.constants.games import HISTORY_PAGE_SIZE_MAX
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    counted_queries,
    create_room,
    create_template,
    place_current_in_first_tier,
    play_and_close,
    register,
    start_game,
)

pytestmark = pytest.mark.integration


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
    """Salle d'Alice (template « Food », 2 tuiles), que Bob a rejointe."""
    template_id: str = create_template(auth_client, db_session, alice, tile_count=2)
    room: JsonObject = create_room(auth_client, alice, template_id)
    assert auth_client.post(f"/rooms/{room['code']}/join", headers=bob).status_code == 200
    return room


def play_a_game(
    client: TestClient,
    room: JsonObject,
    admin: dict[str, str],
    players: list[dict[str, str]],
) -> str:
    """Une partie où ces joueurs placent le premier item, puis close ; renvoie son lien."""
    started: JsonObject = start_game(client, room["code"], admin)
    for player in players:
        place_current_in_first_tier(client, started, player)
    closed: JsonObject = play_and_close(client, room["code"], admin)
    return closed["past_games"][0]["public_token"]


def history(
    client: TestClient, headers: dict[str, str], limit: int | None = None, offset: int = 0
) -> Response:
    params: dict[str, int] = {"offset": offset}
    if limit is not None:
        params["limit"] = limit
    return client.get("/history", params=params, headers=headers)


def tokens(response: Response) -> list[str]:
    return [game["public_token"] for game in response.json()["games"]]


def test_a_player_finds_their_closed_game(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    token: str = play_a_game(auth_client, alice_room, alice, [alice, bob])

    response: Response = history(auth_client, bob)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["has_more"] is False
    assert len(body["games"]) == 1
    game: JsonObject = body["games"][0]
    assert game["public_token"] == token
    assert game["template_name"] == "Food"
    assert game["player_count"] == 2
    assert game["closed_at"] is not None


def test_the_room_admin_who_does_not_play_finds_the_game_too(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    auth_client.patch(
        f"/rooms/{alice_room['code']}/settings", json={"admin_plays": False}, headers=alice
    )
    token: str = play_a_game(auth_client, alice_room, alice, [bob])

    response: Response = history(auth_client, alice)

    # Alice n'est pas une joueuse figée, mais elle animait la partie (permissions.md)
    assert tokens(response) == [token]
    assert response.json()["games"][0]["player_count"] == 1


def test_another_account_does_not_see_the_game(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    play_a_game(auth_client, alice_room, alice, [alice, bob])
    carol: dict[str, str] = register(auth_client, "carol@example.com")

    response: Response = history(auth_client, carol)

    assert response.status_code == 200
    assert response.json() == {"games": [], "has_more": False}


def test_a_game_in_progress_is_not_in_the_history(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    started: JsonObject = start_game(auth_client, alice_room["code"], alice)
    place_current_in_first_tier(auth_client, started, bob)

    assert tokens(history(auth_client, bob)) == []


def test_the_history_goes_from_the_newest_game_page_by_page(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    first: str = play_a_game(auth_client, alice_room, alice, [alice, bob])
    second: str = play_a_game(auth_client, alice_room, alice, [alice, bob])
    third: str = play_a_game(auth_client, alice_room, alice, [alice, bob])

    first_page: Response = history(auth_client, bob, limit=2)
    second_page: Response = history(auth_client, bob, limit=2, offset=2)

    assert tokens(first_page) == [third, second]
    assert first_page.json()["has_more"] is True
    assert tokens(second_page) == [first]
    assert second_page.json()["has_more"] is False


@pytest.mark.parametrize("limit", [0, HISTORY_PAGE_SIZE_MAX + 1])
def test_a_page_size_out_of_bounds_is_refused(
    auth_client: TestClient, alice: dict[str, str], limit: int
):
    assert history(auth_client, alice, limit=limit).status_code == 422


def test_the_history_needs_an_account(auth_client: TestClient):
    response: Response = auth_client.get("/history")

    assert response.status_code == 401


def test_a_deleted_account_leaves_the_history_of_the_others_intact(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    token: str = play_a_game(auth_client, alice_room, alice, [alice, bob])
    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=alice
    )
    assert deleted.status_code == 204

    response: Response = history(auth_client, bob)

    # La salle d'Alice est fermée avec son compte : la partie reste, avec ses deux joueurs
    assert tokens(response) == [token]
    assert response.json()["games"][0]["player_count"] == 2


def test_the_number_of_queries_does_not_grow_with_the_games(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    counts: list[int] = []
    for _ in range(2):
        play_a_game(auth_client, alice_room, alice, [alice, bob])
        with counted_queries(db_session) as statements:
            assert history(auth_client, bob).status_code == 200
        counts.append(len(statements))
    play_a_game(auth_client, alice_room, alice, [alice, bob])
    with counted_queries(db_session) as statements:
        assert history(auth_client, bob).status_code == 200
    counts.append(len(statements))

    # 1, 2 puis 3 parties : autant de requêtes à chaque fois
    assert counts[0] == counts[1] == counts[2], counts
