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
from app.models.enums import GameStatus, PlacementPhase
from app.models.game import Game
from app.models.participant import Participant
from app.schemas.room_events import CooldownStartedEvent, RoundStartedEvent
from app.services.games import GameService
from app.services.rooms import RoomService
from app.services.templates import TemplateService
from tests.integration.conftest import RecordingRoomEventPublisher, RecordingRoundScheduler
from tests.integration.helpers import JsonObject, create_room, create_template, register

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


def settings(client: TestClient, code: str, headers: dict[str, str], **changes: object) -> None:
    response: Response = client.patch(f"/rooms/{code}/settings", json=changes, headers=headers)
    assert response.status_code == 200


def join(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/join", headers=headers)
    assert response.status_code == 200
    return response.json()


def start(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/game", headers=headers)
    assert response.status_code == 201
    return response.json()


def next_round(client: TestClient, code: str, headers: dict[str, str]) -> Response:
    return client.post(f"/rooms/{code}/game/next", headers=headers)


def place_current(
    client: TestClient, db_session: Session, code: str, headers: dict[str, str]
) -> Response:
    """Place l'item en cours en tête du premier tier."""
    game: Game = stored_game(db_session)
    tier_id: uuid.UUID = game.snapshot.tiers[0].id
    return client.put(
        f"/rooms/{code}/game/placements/{game.current_round.snapshot_tile_id}",
        json={"tier_id": str(tier_id), "position": 0},
        headers=headers,
    )


def stored_game(db_session: Session) -> Game:
    game: Game = db_session.scalars(select(Game)).one()
    db_session.refresh(game)
    return game


def room_id_of_game(db_session: Session) -> uuid.UUID:
    room_id: uuid.UUID | None = stored_game(db_session).room_id
    assert room_id is not None
    return room_id


def set_connected(db_session: Session, connected_names: set[str]) -> None:
    """Présence des participants, sans canal : connectés ceux de connected_names."""
    for participant in db_session.scalars(select(Participant)):
        participant.connected = participant.display_name in connected_names
    db_session.flush()


def absent_tiles(db_session: Session, display_name: str) -> list[str | None]:
    """Textes des items pour lesquels ce participant a un vote absent, dans l'ordre des tours."""
    participant: Participant = db_session.scalars(
        select(Participant).where(Participant.user.has(display_name=display_name))
    ).one()
    game: Game = stored_game(db_session)
    absent_ids: set[uuid.UUID] = {
        placement.snapshot_tile_id
        for placement in game.placements
        if placement.participant_id == participant.id
        and placement.phase == PlacementPhase.ROUND
        and placement.is_absent
    }
    return [game_round.tile.text for game_round in game.rounds if game_round.tile.id in absent_ids]


def game_service(
    db_session: Session, publisher: RecordingRoomEventPublisher, scheduler: RecordingRoundScheduler
) -> GameService:
    """Le service hors requête, comme le lancent les timers et le canal."""
    rooms: RoomService = RoomService(db_session, get_settings(), publisher)
    return GameService(
        db_session, publisher, rooms, TemplateService(db_session, get_settings()), scheduler
    )


# --- « Suivant » ------------------------------------------------------------------------------


def test_the_admin_moves_to_the_next_item(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    start(auth_client, code, alice)
    placed: JsonObject = place_current(auth_client, db_session, code, alice).json()

    response: Response = next_round(auth_client, code, alice)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["game"]["round_number"] == 2
    assert body["game"]["current_item"]["text"] == "Tile 1"
    assert body["game"]["placed_participant_ids"] == []
    assert body["version"] == placed["version"] + 1
    assert stored_game(db_session).rounds[0].ended_at is not None
    # Bob n'avait pas placé l'item : vote absent ; Alice l'avait placé
    assert absent_tiles(db_session, "bob") == ["Tile 0"]
    assert absent_tiles(db_session, "alice") == []
    started: object = room_events.events[-1][1]
    assert isinstance(started, RoundStartedEvent)
    assert started.room_version == body["version"]
    assert (started.data.round_number, started.data.round_count) == (2, TILE_COUNT)


def test_a_player_cannot_move_to_the_next_item(
    auth_client: TestClient, alice: dict[str, str], bob: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    start(auth_client, code, alice)

    response: Response = next_round(auth_client, code, bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_next_is_refused_without_a_game(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = next_round(auth_client, alice_room["code"], alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ROUND_NOT_IN_PROGRESS


def test_the_last_round_starts_the_cooldown(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    start(auth_client, code, alice)
    for _ in range(TILE_COUNT - 1):
        next_round(auth_client, code, alice)

    response: Response = next_round(auth_client, code, alice)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert body["game"]["status"] == "cooldown"
    game: Game = stored_game(db_session)
    assert game.status == GameStatus.COOLDOWN
    assert game.cooldown_ends_at is not None
    expected_end: datetime = datetime.now(UTC) + timedelta(
        seconds=alice_room["settings"]["cooldown_seconds"]
    )
    assert abs((game.cooldown_ends_at - expected_end).total_seconds()) < 5
    cooldown: object = room_events.events[-1][1]
    assert isinstance(cooldown, CooldownStartedEvent)
    assert cooldown.data.ends_at == game.cooldown_ends_at
    # Plus aucun tour à terminer
    again: Response = next_round(auth_client, code, alice)
    assert again.status_code == 409
    assert again.json()["code"] == ErrorCode.ROUND_NOT_IN_PROGRESS


# --- Timer ------------------------------------------------------------------------------------


def test_a_timer_is_scheduled_for_each_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="timer", timer_seconds=20)
    start(auth_client, code, alice)
    next_round(auth_client, code, alice)

    game: Game = stored_game(db_session)
    assert round_scheduler.deadlines == [
        (game.id, 1, game.rounds[0].ends_at),
        (game.id, 2, game.rounds[1].ends_at),
    ]


def test_the_timer_ends_its_round_only_once(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="timer", timer_seconds=20)
    start(auth_client, code, alice)
    game_id: uuid.UUID = stored_game(db_session).id
    service: GameService = game_service(db_session, room_events, round_scheduler)

    service.end_round_on_timer(game_id, 1)
    event_count: int = len(room_events.events)
    # En retard, ou après un « suivant » : le tour 1 n'est plus en cours, rien ne change
    service.end_round_on_timer(game_id, 1)

    assert stored_game(db_session).current_round_number == 2
    assert len(room_events.events) == event_count
    assert room_events.types()[-1] == "round.started"


def test_pending_deadlines_are_scheduled_again_at_startup(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="timer", timer_seconds=20)
    start(auth_client, code, alice)
    next_round(auth_client, code, alice)
    recorded: RecordingRoundScheduler = RecordingRoundScheduler()
    monkeypatch.setattr(main_module, "round_timers", recorded)

    # Un redémarrage : les timers en mémoire sont perdus, la base garde la fin du tour en cours
    main_module._reschedule_rounds(lambda: nullcontext(db_session))

    game: Game = stored_game(db_session)
    assert recorded.deadlines == [(game.id, 2, game.rounds[1].ends_at)]


# --- « Tout le monde a placé » ------------------------------------------------------------------


def test_everyone_placed_ends_the_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="everyone_placed")
    join(auth_client, code, bob)
    start(auth_client, code, alice)
    set_connected(db_session, {"alice", "bob"})

    place_current(auth_client, db_session, code, alice)
    assert stored_game(db_session).current_round_number == 1
    response: Response = place_current(auth_client, db_session, code, bob)

    assert response.json()["game"]["round_number"] == 2
    assert room_events.types()[-3:] == ["participant.placed", "participant.placed", "round.started"]


def test_a_disconnected_player_is_not_waited_for(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="everyone_placed")
    join(auth_client, code, bob)
    start(auth_client, code, alice)
    set_connected(db_session, {"alice"})

    response: Response = place_current(auth_client, db_session, code, alice)

    assert response.json()["game"]["round_number"] == 2
    # Bob, déconnecté, a un vote absent pour l'item
    assert absent_tiles(db_session, "bob") == ["Tile 0"]


def test_a_departure_can_end_the_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="everyone_placed")
    join(auth_client, code, bob)
    start(auth_client, code, alice)
    set_connected(db_session, {"alice", "bob"})
    place_current(auth_client, db_session, code, alice)

    set_connected(db_session, {"alice"})
    game_service(db_session, room_events, round_scheduler).advance_if_everyone_placed(
        room_id_of_game(db_session)
    )

    assert stored_game(db_session).current_round_number == 2


def test_removing_the_last_awaited_player_ends_the_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="everyone_placed")
    joined: JsonObject = join(auth_client, code, bob)
    start(auth_client, code, alice)
    set_connected(db_session, {"alice", "bob"})
    place_current(auth_client, db_session, code, alice)
    bob_id: str = next(
        participant["id"]
        for participant in joined["participants"]
        if participant["display_name"] == "bob"
    )

    response: Response = auth_client.delete(f"/rooms/{code}/participants/{bob_id}", headers=alice)

    assert response.status_code == 200
    assert response.json()["game"]["round_number"] == 2


def test_nobody_connected_does_not_end_the_round(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    code: str = alice_room["code"]
    settings(auth_client, code, alice, auto_advance="everyone_placed")
    start(auth_client, code, alice)
    set_connected(db_session, set())

    place_current(auth_client, db_session, code, alice)
    game_service(db_session, room_events, round_scheduler).advance_if_everyone_placed(
        room_id_of_game(db_session)
    )

    assert stored_game(db_session).current_round_number == 1


def test_without_automatic_setting_the_round_waits_for_the_admin(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    join(auth_client, code, bob)
    start(auth_client, code, alice)
    set_connected(db_session, {"alice", "bob"})

    place_current(auth_client, db_session, code, alice)
    place_current(auth_client, db_session, code, bob)

    assert stored_game(db_session).current_round_number == 1


# --- Retardataire -----------------------------------------------------------------------------


def test_a_late_joiner_gets_absent_votes_for_the_past_rounds(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    start(auth_client, code, alice)
    next_round(auth_client, code, alice)

    join(auth_client, code, bob)

    # Le tour 1 est fini, le tour 2 est en cours : Bob peut encore placer Tile 1
    assert absent_tiles(db_session, "bob") == ["Tile 0"]
    # Alice n'avait pas placé Tile 0 non plus : vote absent à la fin du tour 1
    assert absent_tiles(db_session, "alice") == ["Tile 0"]
