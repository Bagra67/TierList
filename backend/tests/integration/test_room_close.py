"""Fermeture d'une salle (US-2.7) : la salle disparaît avec ses places, ses parties lui survivent ;
une partie en cours est close d'abord."""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import GameStatus, PlacementPhase
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.participant import Participant
from app.models.room import Room
from tests.integration.conftest import RecordingRoomEventPublisher, RecordingRoundScheduler
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    create_room,
    create_template,
    next_item,
    place_current_in_first_tier,
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
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
) -> JsonObject:
    """Salle d'Alice, que Bob a rejointe."""
    template_id: str = create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)
    room: JsonObject = create_room(auth_client, alice, template_id)
    assert auth_client.post(f"/rooms/{room['code']}/join", headers=bob).status_code == 200
    return room


def close(client: TestClient, code: str, headers: dict[str, str]) -> Response:
    return client.delete(f"/rooms/{code}", headers=headers)


def room_id(db_session: Session) -> uuid.UUID:
    return db_session.scalars(select(Room.id)).one()


def stored_game(db_session: Session) -> Game:
    game: Game = db_session.scalars(select(Game)).one()
    db_session.refresh(game)
    return game


def test_closing_deletes_the_room_and_its_seats(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    closed_id: uuid.UUID = room_id(db_session)

    response: Response = close(auth_client, alice_room["code"], alice)

    assert response.status_code == 204
    assert auth_client.get(f"/rooms/{alice_room['code']}", headers=alice).status_code == 404
    assert db_session.scalars(select(Room)).all() == []
    assert db_session.scalars(select(Participant)).all() == []
    # Tous les sockets de la salle sont fermés, après le commit
    assert room_events.closed_rooms == [closed_id]


def test_only_the_room_admin_closes_the_room(
    auth_client: TestClient,
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = close(auth_client, alice_room["code"], bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED
    assert room_events.closed_rooms == []


def test_closing_an_unknown_room_is_not_found(auth_client: TestClient, alice: dict[str, str]):
    response: Response = close(auth_client, "ZZZZZZ", alice)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_closing_during_a_round_closes_the_game_with_its_rankings(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    started: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, started, alice)
    place_current_in_first_tier(auth_client, started, bob)
    second: JsonObject = next_item(auth_client, code, alice)
    # Seule Alice place le deuxième item avant la fermeture
    place_current_in_first_tier(auth_client, second, alice)

    assert close(auth_client, code, alice).status_code == 204

    game: Game = stored_game(db_session)
    assert game.status == GameStatus.CLOSED
    assert game.closed_at is not None
    assert game.room_id is None
    assert all(game_round.ended_at is not None for game_round in game.rounds[:2])
    # Les classements du moment deviennent les plateaux finaux, rattachés aux joueurs figés
    finals: dict[str, int] = {}
    for placement in game.placements:
        assert placement.participant_id is None
        if placement.phase == PlacementPhase.FINAL:
            assert placement.player is not None
            name: str = placement.player.display_name
            finals[name] = finals.get(name, 0) + 1
    assert finals == {"alice": 2, "bob": 1}
    # L'item interrompu ne donne pas de vote absent à Bob
    assert not any(placement.is_absent for placement in game.placements)


def test_closing_during_the_cooldown_keeps_the_final_boards(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    room: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, room, alice)
    while room["game"]["status"] == "in_round":
        room = next_item(auth_client, code, alice)

    assert close(auth_client, code, alice).status_code == 204

    game: Game = stored_game(db_session)
    assert game.status == GameStatus.CLOSED
    assert sorted(player.display_name for player in game.players) == ["alice", "bob"]
    final_owners: list[str] = [
        placement.player.display_name
        for placement in game.placements
        if placement.phase == PlacementPhase.FINAL and placement.player is not None
    ]
    assert final_owners == ["alice"]


def test_a_game_closed_earlier_survives_its_room(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    room: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, room, alice)
    while room["game"]["status"] == "in_round":
        room = next_item(auth_client, code, alice)
    assert auth_client.post(f"/rooms/{code}/game/end", headers=alice).status_code == 200
    closed_at = stored_game(db_session).closed_at

    assert close(auth_client, code, alice).status_code == 204

    game: Game = stored_game(db_session)
    assert game.room_id is None
    assert game.closed_at == closed_at
    assert len(db_session.scalars(select(GamePlayer)).all()) == 2
    assert game.placements


def test_deleting_the_admin_account_closes_their_room_and_its_game(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    started: JsonObject = start_game(auth_client, alice_room["code"], alice)
    place_current_in_first_tier(auth_client, started, bob)
    closed_id: uuid.UUID = room_id(db_session)

    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=alice
    )

    assert deleted.status_code == 204
    assert db_session.scalars(select(Room)).all() == []
    game: Game = stored_game(db_session)
    # La partie est close au lieu de rester orpheline, et le classement de Bob est gardé
    assert game.status == GameStatus.CLOSED
    assert [player.display_name for player in game.players] == ["bob"]
    assert room_events.closed_rooms == [closed_id]


def test_a_wrong_password_keeps_the_admin_rooms(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": "wrong password"}, headers=alice
    )

    assert deleted.status_code == 403
    assert len(db_session.scalars(select(Room)).all()) == 1
    assert room_events.closed_rooms == []
