"""Retour à sa place pendant une partie (US-4.4) et arrivée en cours de partie (US-4.5)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import PlacementPhase
from app.models.game import Game
from app.models.participant import Participant
from tests.integration.helpers import (
    JsonObject,
    board,
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
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)
    return create_room(auth_client, alice, template_id)


def join(client: TestClient, code: str, headers: dict[str, str]) -> Response:
    return client.post(f"/rooms/{code}/join", headers=headers)


def your_seat(room: JsonObject) -> str:
    return next(participant["id"] for participant in room["participants"] if participant["is_you"])


def absent_tiles(db_session: Session, seat_id: str) -> list[str | None]:
    """Textes des items pour lesquels cette place a un vote absent, dans l'ordre des tours."""
    game: Game = db_session.scalars(select(Game)).one()
    db_session.refresh(game)
    absent_ids: set[uuid.UUID] = {
        placement.snapshot_tile_id
        for placement in game.placements
        if placement.participant_id == uuid.UUID(seat_id)
        and placement.phase == PlacementPhase.ROUND
        and placement.is_absent
    }
    return [game_round.tile.text for game_round in game.rounds if game_round.tile.id in absent_ids]


def disconnect(db_session: Session, seat_id: str) -> None:
    """Le canal temps réel de cette place se ferme (sans websocket dans ces tests)."""
    participant: Participant | None = db_session.get(Participant, uuid.UUID(seat_id))
    assert participant is not None
    participant.connected = False
    db_session.flush()


# --- Retour à sa place --------------------------------------------------------------------------


def test_an_account_finds_its_ranking_and_the_current_round_when_coming_back(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    joined: JsonObject = join(auth_client, code, bob).json()
    started: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, started, bob)
    bob_seat: str = your_seat(joined)
    disconnect(db_session, bob_seat)
    # Pendant son absence, deux tours se terminent : il avait placé le premier, pas le second
    next_item(auth_client, code, alice)
    version: int = next_item(auth_client, code, alice)["version"]

    comeback: Response = join(auth_client, code, bob)

    assert comeback.status_code == 200
    room: JsonObject = auth_client.get(f"/rooms/{code}", headers=bob).json()
    assert your_seat(room) == bob_seat
    assert room["version"] == version
    assert room["game"]["round_number"] == 3
    assert room["game"]["current_item"]["text"] == "Tile 2"
    assert board(room) == [("S", "Tile 0", 0)]
    assert absent_tiles(db_session, bob_seat) == ["Tile 1"]


def test_a_participant_comes_back_to_a_game_whose_arrivals_are_locked(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    start_game(auth_client, code, alice)
    locked: Response = auth_client.patch(
        f"/rooms/{code}/settings", json={"late_arrivals_allowed": False}, headers=alice
    )
    assert locked.status_code == 200
    carol: dict[str, str] = register(auth_client, "carol@example.com")

    assert join(auth_client, code, bob).status_code == 200
    newcomer: Response = join(auth_client, code, carol)
    assert newcomer.status_code == 409
    assert newcomer.json()["code"] == ErrorCode.ROOM_LOCKED


def test_a_guest_comes_back_with_the_cookie_or_the_personal_link(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    guest: JsonObject = auth_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"}).json()
    token: str = guest["guest_link"].split("#guest=", 1)[1]
    lou_seat: str = your_seat(guest)
    started: JsonObject = start_game(auth_client, code, alice)
    # Sans en-tête : le cookie du navigateur de Lou
    place_current_in_first_tier(auth_client, started)
    disconnect(db_session, lou_seat)
    next_item(auth_client, code, alice)

    # Même navigateur : le cookie suffit
    same_browser: JsonObject = auth_client.get(f"/rooms/{code}").json()
    # Autre appareil, sans cookie : le lien personnel
    auth_client.cookies.clear()
    other_device: Response = auth_client.post(f"/rooms/{code}/guest-session", json={"token": token})

    assert other_device.status_code == 200
    for room in (same_browser, other_device.json()):
        assert your_seat(room) == lou_seat
        assert room["game"]["round_number"] == 2
        assert board(room) == [("S", "Tile 0", 0)]


# --- Arrivée en cours de partie -----------------------------------------------------------------


def test_a_late_joiner_during_the_cooldown_is_absent_for_every_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    for _ in range(TILE_COUNT):
        next_item(auth_client, code, alice)

    joined: Response = join(auth_client, code, bob)

    assert joined.status_code == 200
    assert joined.json()["game"]["status"] == "cooldown"
    assert absent_tiles(db_session, your_seat(joined.json())) == ["Tile 0", "Tile 1", "Tile 2"]
