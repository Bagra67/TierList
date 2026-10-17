"""Cooldown final (US-4.1, US-4.2, US-4.6) : plateau final, rattrapage des items manqués et fin
du cooldown (timer ou « Terminer maintenant »)."""

import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import main as main_module
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.models.enums import GameStatus, PlacementPhase, RoomStatus
from app.models.game import Game
from app.models.placement import Placement
from app.models.room import Room
from app.schemas.room_events import GameClosedEvent
from app.services.games import GameService
from app.services.rooms import RoomService
from app.services.templates import TemplateService
from tests.integration.conftest import RecordingRoomEventPublisher, RecordingRoundScheduler
from tests.integration.helpers import (
    JsonObject,
    board,
    create_room,
    create_template,
    next_item,
    place,
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


def stored_game(db_session: Session) -> Game:
    game: Game = db_session.scalars(select(Game)).one()
    db_session.refresh(game)
    return game


def tile_id(db_session: Session, text: str) -> str:
    game: Game = stored_game(db_session)
    return next(
        str(game_round.tile.id) for game_round in game.rounds if game_round.tile.text == text
    )


def tier_id(db_session: Session, name: str) -> str:
    return next(
        str(tier.id) for tier in stored_game(db_session).snapshot.tiers if tier.name == name
    )


def to_cooldown(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    """Termine les tours restants : la partie passe en cooldown."""
    room: JsonObject = client.get(f"/rooms/{code}", headers=headers).json()
    while room["game"]["status"] == "in_round":
        room = next_item(client, code, headers)
    return room


def placements_of(db_session: Session, text: str, phase: PlacementPhase) -> list[Placement]:
    """Placements de cette tuile pour cette phase, toutes places confondues."""
    game: Game = stored_game(db_session)
    return [
        placement
        for placement in game.placements
        if placement.tile.text == text and placement.phase == phase
    ]


def missed(room: JsonObject) -> list[str | None]:
    return [item["text"] for item in room["game"]["missed_items"]]


def game_service(
    db_session: Session, publisher: RecordingRoomEventPublisher, scheduler: RecordingRoundScheduler
) -> GameService:
    """Le service hors requête, comme le lancent les timers."""
    rooms: RoomService = RoomService(db_session, get_settings(), publisher)
    return GameService(
        db_session, publisher, rooms, TemplateService(db_session, get_settings()), scheduler
    )


@pytest.fixture
def alice_in_cooldown(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
) -> JsonObject:
    """Alice a placé Tile 0 en S, puis Tile 1 en tête de S ; elle a manqué Tile 2."""
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    assert (
        place(
            auth_client, code, tile_id(db_session, "Tile 0"), tier_id(db_session, "S"), 0, alice
        ).status_code
        == 200
    )
    next_item(auth_client, code, alice)
    assert (
        place(
            auth_client, code, tile_id(db_session, "Tile 1"), tier_id(db_session, "S"), 0, alice
        ).status_code
        == 200
    )
    return to_cooldown(auth_client, code, alice)


# --- Plateau final --------------------------------------------------------------------------------


def test_the_final_board_starts_as_a_copy_of_the_round_board(
    db_session: Session, alice_in_cooldown: JsonObject
):
    assert alice_in_cooldown["game"]["status"] == "cooldown"
    assert board(alice_in_cooldown) == [("S", "Tile 1", 0), ("S", "Tile 0", 1)]
    assert missed(alice_in_cooldown) == ["Tile 2"]
    # Un placement final par placement de tour ; le vote absent n'est pas copié
    finals: list[Placement] = placements_of(db_session, "Tile 0", PlacementPhase.FINAL)
    assert [(final.position, final.is_absent) for final in finals] == [(1, False)]
    assert placements_of(db_session, "Tile 2", PlacementPhase.FINAL) == []


def test_a_move_in_the_cooldown_only_changes_the_final_placement(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    alice_in_cooldown: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    event_count: int = len(room_events.events)

    response: Response = place(
        auth_client,
        alice_room["code"],
        tile_id(db_session, "Tile 0"),
        tier_id(db_session, "A"),
        0,
        alice,
    )

    assert response.status_code == 200
    moved: JsonObject = response.json()
    assert board(moved) == [("S", "Tile 1", 0), ("A", "Tile 0", 0)]
    # Plateau privé : ni version, ni événement
    assert moved["version"] == alice_in_cooldown["version"]
    assert len(room_events.events) == event_count
    # Les deux placements sont gardés (US-4.2) : celui du tour n'a pas bougé
    (round_placement,) = placements_of(db_session, "Tile 0", PlacementPhase.ROUND)
    assert (str(round_placement.snapshot_tier_id), round_placement.position) == (
        tier_id(db_session, "S"),
        1,
    )


def test_a_missed_item_is_caught_up_and_keeps_its_absent_vote(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    alice_in_cooldown: JsonObject,
):
    response: Response = place(
        auth_client,
        alice_room["code"],
        tile_id(db_session, "Tile 2"),
        tier_id(db_session, "S"),
        1,
        alice,
    )

    assert response.status_code == 200
    assert board(response.json()) == [("S", "Tile 1", 0), ("S", "Tile 2", 1), ("S", "Tile 0", 2)]
    assert missed(response.json()) == []
    (round_placement,) = placements_of(db_session, "Tile 2", PlacementPhase.ROUND)
    assert round_placement.is_absent


def test_a_late_joiner_catches_up_every_item(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    to_cooldown(auth_client, code, alice)
    joined: JsonObject = auth_client.post(f"/rooms/{code}/join", headers=bob).json()
    assert missed(joined) == ["Tile 0", "Tile 1", "Tile 2"]

    response: Response = place(
        auth_client, code, tile_id(db_session, "Tile 1"), tier_id(db_session, "A"), 0, bob
    )

    assert response.status_code == 200
    assert board(response.json()) == [("A", "Tile 1", 0)]
    assert missed(response.json()) == ["Tile 0", "Tile 2"]


def test_placing_in_the_cooldown_checks_the_tile_and_the_tier(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    alice_in_cooldown: JsonObject,
):
    code: str = alice_room["code"]

    unknown_tile: Response = place(
        auth_client, code, str(uuid.uuid4()), tier_id(db_session, "S"), 0, alice
    )
    unknown_tier: Response = place(
        auth_client, code, tile_id(db_session, "Tile 2"), str(uuid.uuid4()), 0, alice
    )

    assert unknown_tile.status_code == 404
    assert unknown_tile.json()["code"] == ErrorCode.ITEM_NOT_IN_GAME
    assert unknown_tier.status_code == 404
    assert unknown_tier.json()["code"] == ErrorCode.TIER_NOT_FOUND


def test_the_admin_who_does_not_play_cannot_place_in_the_cooldown(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    auth_client.post(f"/rooms/{code}/join", headers=bob)
    auth_client.patch(f"/rooms/{code}/settings", json={"admin_plays": False}, headers=alice)
    start_game(auth_client, code, alice)
    cooldown: JsonObject = to_cooldown(auth_client, code, alice)
    # Ni plateau ni item manqué pour elle : elle ne place pas les items
    assert cooldown["game"]["own_placements"] == []
    assert missed(cooldown) == []

    response: Response = place(
        auth_client, code, tile_id(db_session, "Tile 0"), tier_id(db_session, "S"), 0, alice
    )

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.NOT_A_PLACING_PARTICIPANT


def test_placing_after_the_end_of_the_cooldown_is_refused(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    alice_in_cooldown: JsonObject,
):
    # La fin du cooldown est passée, son timer pas encore
    game: Game = stored_game(db_session)
    game.cooldown_ends_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response: Response = place(
        auth_client,
        alice_room["code"],
        tile_id(db_session, "Tile 2"),
        tier_id(db_session, "S"),
        0,
        alice,
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.COOLDOWN_OVER


# --- Fin du cooldown ------------------------------------------------------------------------------


def test_the_admin_ends_the_cooldown_and_the_game_is_closed(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    alice_in_cooldown: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = auth_client.post(f"/rooms/{alice_room['code']}/game/end", headers=alice)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["game"] is None
    assert body["status"] == "open"
    assert body["version"] == alice_in_cooldown["version"] + 1
    game: Game = stored_game(db_session)
    assert game.status == GameStatus.CLOSED
    assert game.closed_at is not None
    room: Room = db_session.scalars(select(Room)).one()
    assert room.status == RoomStatus.OPEN
    closed: object = room_events.events[-1][1]
    assert isinstance(closed, GameClosedEvent)
    assert closed.data.game_id == game.id
    assert closed.room_version == body["version"]


def test_a_player_cannot_end_the_cooldown(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    auth_client.post(f"/rooms/{code}/join", headers=bob)
    start_game(auth_client, code, alice)
    to_cooldown(auth_client, code, alice)

    response: Response = auth_client.post(f"/rooms/{code}/game/end", headers=bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_ending_is_refused_outside_the_cooldown(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)

    response: Response = auth_client.post(f"/rooms/{code}/game/end", headers=alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.COOLDOWN_NOT_IN_PROGRESS


def test_the_cooldown_timer_closes_the_game_only_once(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    to_cooldown(auth_client, code, alice)
    game: Game = stored_game(db_session)
    assert round_scheduler.cooldown_ends == [(game.id, game.cooldown_ends_at)]
    service: GameService = game_service(db_session, room_events, round_scheduler)

    service.end_cooldown_on_timer(game.id)
    event_count: int = len(room_events.events)
    # En retard, ou après « Terminer maintenant » : plus de cooldown, rien ne change
    service.end_cooldown_on_timer(game.id)

    assert stored_game(db_session).status == GameStatus.CLOSED
    assert len(room_events.events) == event_count
    assert room_events.types()[-1] == "game.closed"


def test_a_late_round_timer_does_not_close_the_game(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    to_cooldown(auth_client, code, alice)

    # Le timer du dernier tour, terminé avant par « suivant »
    game_service(db_session, room_events, round_scheduler).end_round_on_timer(
        stored_game(db_session).id, TILE_COUNT
    )

    assert stored_game(db_session).status == GameStatus.COOLDOWN


def test_pending_cooldown_ends_are_scheduled_again_at_startup(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
):
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    to_cooldown(auth_client, code, alice)
    recorded: RecordingRoundScheduler = RecordingRoundScheduler()
    monkeypatch.setattr(main_module, "round_timers", recorded)

    # Un redémarrage : les timers en mémoire sont perdus, la base garde la fin du cooldown
    main_module._reschedule_rounds(lambda: nullcontext(db_session))

    game: Game = stored_game(db_session)
    assert recorded.cooldown_ends == [(game.id, game.cooldown_ends_at)]
