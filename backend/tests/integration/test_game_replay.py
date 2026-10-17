"""Rejouer dans la même salle (US-2.9) : après une partie close, une nouvelle partie se lance
avec le même lien et le même code, sur la version courante du template, avec les participants
encore dans la salle."""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.tile import Tile
from tests.integration.helpers import (
    JsonObject,
    create_room,
    create_template,
    place_current_in_first_tier,
    play_and_close,
    register,
    start_game,
)

pytestmark = pytest.mark.integration

TILE_COUNT = 2


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)


@pytest.fixture
def first_game_closed(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    template_id: str,
) -> JsonObject:
    """Salle d'Alice que Bob a rejointe ; une première partie jouée par les deux, puis close."""
    room: JsonObject = create_room(auth_client, alice, template_id)
    assert auth_client.post(f"/rooms/{room['code']}/join", headers=bob).status_code == 200
    started: JsonObject = start_game(auth_client, room["code"], alice)
    place_current_in_first_tier(auth_client, started, alice)
    place_current_in_first_tier(auth_client, started, bob)
    return play_and_close(auth_client, room["code"], alice)


def games_by_start(db_session: Session) -> list[Game]:
    games: list[Game] = list(db_session.scalars(select(Game).order_by(Game.started_at)).all())
    for game in games:
        db_session.refresh(game)
    return games


def test_playing_again_keeps_the_room_its_link_and_its_past_game(
    auth_client: TestClient, alice: dict[str, str], first_game_closed: JsonObject
):
    code: str = first_game_closed["code"]

    replayed: JsonObject = start_game(auth_client, code, alice)

    assert replayed["code"] == code
    assert replayed["link"] == first_game_closed["link"]
    assert replayed["status"] == "playing"
    assert replayed["game"]["round_number"] == 1
    # La partie close reste dans les parties passées, avec son lien de résultats
    assert replayed["past_games"] == first_game_closed["past_games"]


def test_the_new_game_uses_the_current_version_of_the_template(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    template_id: str,
    first_game_closed: JsonObject,
):
    # Entre les deux parties, Alice ajoute une tuile à son template
    db_session.add(Tile(template_id=uuid.UUID(template_id), text="New tile", position=TILE_COUNT))
    db_session.flush()

    replayed: JsonObject = start_game(auth_client, first_game_closed["code"], alice)

    assert replayed["game"]["round_count"] == TILE_COUNT + 1
    first, second = games_by_start(db_session)
    assert first.snapshot_id != second.snapshot_id
    # La partie close garde sa version figée (invariant 4)
    assert len(first.snapshot.tiles) == TILE_COUNT
    assert [tile.text for tile in second.snapshot.tiles][-1] == "New tile"


def test_the_new_game_is_played_by_the_participants_still_in_the_room(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    first_game_closed: JsonObject,
):
    code: str = first_game_closed["code"]
    bob_id: str = next(
        participant["id"]
        for participant in first_game_closed["participants"]
        if participant["display_name"] == "bob"
    )
    # Bob quitte la salle, Carol arrive
    removed: Response = auth_client.delete(f"/rooms/{code}/participants/{bob_id}", headers=alice)
    assert removed.status_code == 200
    carol: dict[str, str] = register(auth_client, "carol@example.com")
    assert auth_client.post(f"/rooms/{code}/join", headers=carol).status_code == 200

    replayed: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, replayed, alice)
    place_current_in_first_tier(auth_client, replayed, carol)
    play_and_close(auth_client, code, alice)

    first, second = games_by_start(db_session)
    assert sorted(player.display_name for player in first.players) == ["alice", "bob"]
    assert sorted(player.display_name for player in second.players) == ["alice", "carol"]
