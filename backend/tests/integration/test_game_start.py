from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.game import Game, GameStatus
from app.models.image import Image
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.template_snapshot import TemplateSnapshot
from app.models.tile import Tile
from app.models.user import User
from app.schemas.room_events import GameStartedEvent
from app.services import games as games_module
from tests.integration.conftest import FAKE_IMAGE_BASE_URL, RecordingRoomEventPublisher
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
def template_id(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> str:
    return create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)


@pytest.fixture
def alice_room(auth_client: TestClient, alice: dict[str, str], template_id: str) -> JsonObject:
    return create_room(auth_client, alice, template_id)


def start(client: TestClient, code: str, headers: dict[str, str]) -> Response:
    return client.post(f"/rooms/{code}/game", headers=headers)


def change_settings(
    client: TestClient, code: str, headers: dict[str, str], **changes: object
) -> None:
    response: Response = client.patch(f"/rooms/{code}/settings", json=changes, headers=headers)
    assert response.status_code == 200


def stored_game(db_session: Session) -> Game:
    return db_session.scalars(select(Game)).one()


def round_texts(game: Game) -> list[str | None]:
    return [game_round.tile.text for game_round in game.rounds]


# --- Démarrage ------------------------------------------------------------------------------


def test_the_admin_starts_a_game_on_the_first_item(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 201
    body: JsonObject = response.json()
    assert body["status"] == "playing"
    assert body["version"] == alice_room["version"] + 1
    assert body["game"] == {
        "round_number": 1,
        "round_count": TILE_COUNT,
        "current_item": {
            "id": body["game"]["current_item"]["id"],
            "text": "Tile 0",
            "image_url": None,
        },
        "ends_at": None,
    }
    started: object = room_events.events[-1][1]
    assert isinstance(started, GameStartedEvent)
    assert started.room_version == body["version"]
    assert (started.data.round_number, started.data.round_count) == (1, TILE_COUNT)


def test_the_game_is_played_on_a_snapshot_with_one_round_per_tile(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    start(auth_client, alice_room["code"], alice)

    game: Game = stored_game(db_session)
    assert game.status == GameStatus.IN_ROUND
    assert game.current_round_number == 1
    assert game.admin_plays is True
    assert [game_round.number for game_round in game.rounds] == [1, 2, 3]
    assert round_texts(game) == ["Tile 0", "Tile 1", "Tile 2"]
    # Les tours désignent les tuiles de la version figée, jamais celles du template
    snapshot_tile_ids: set[object] = {tile.id for tile in game.snapshot.tiles}
    assert {game_round.snapshot_tile_id for game_round in game.rounds} == snapshot_tile_ids
    assert game.rounds[0].started_at is not None
    assert all(game_round.started_at is None for game_round in game.rounds[1:])
    assert db_session.scalar(select(func.count()).select_from(TemplateSnapshot)) == 1


def test_editing_the_template_does_not_change_the_game_in_progress(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    start(auth_client, alice_room["code"], alice)
    tile: Tile = db_session.scalars(select(Tile).where(Tile.text == "Tile 0")).one()
    tile.text = "Edited"
    db_session.flush()

    room: JsonObject = auth_client.get(f"/rooms/{alice_room['code']}", headers=alice).json()

    assert room["game"]["current_item"]["text"] == "Tile 0"


def test_the_current_item_shows_its_image(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    owner: User = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    image: Image = Image(
        owner_id=owner.id,
        storage_key="first-tile.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
    )
    db_session.add(image)
    db_session.scalars(select(Tile).where(Tile.text == "Tile 0")).one().image = image
    db_session.flush()

    response: Response = start(auth_client, alice_room["code"], alice)

    current_item: JsonObject = response.json()["game"]["current_item"]
    assert current_item["image_url"] == f"{FAKE_IMAGE_BASE_URL}/first-tile.webp"


def test_random_order_shuffles_the_items(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
):
    def reverse(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
        return list(reversed(tiles))

    monkeypatch.setattr(games_module, "shuffle_items", reverse)
    change_settings(auth_client, alice_room["code"], alice, item_order="random")

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.json()["game"]["current_item"]["text"] == "Tile 2"
    assert round_texts(stored_game(db_session)) == ["Tile 2", "Tile 1", "Tile 0"]


def test_the_template_order_is_kept_without_shuffling(
    auth_client: TestClient,
    alice: dict[str, str],
    alice_room: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
):
    def must_not_shuffle(tiles: Sequence[SnapshotTile]) -> list[SnapshotTile]:
        raise AssertionError("the template order must not be shuffled")

    monkeypatch.setattr(games_module, "shuffle_items", must_not_shuffle)

    assert start(auth_client, alice_room["code"], alice).status_code == 201


def test_the_first_round_ends_with_the_timer(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    change_settings(auth_client, alice_room["code"], alice, auto_advance="timer", timer_seconds=20)

    response: Response = start(auth_client, alice_room["code"], alice)

    ends_at: datetime = datetime.fromisoformat(response.json()["game"]["ends_at"])
    assert abs(ends_at - (datetime.now(UTC) + timedelta(seconds=20))) < timedelta(seconds=5)


def test_an_admin_who_does_not_play_starts_with_a_player(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    change_settings(auth_client, alice_room["code"], alice, admin_plays=False)
    auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob)

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 201
    assert stored_game(db_session).admin_plays is False


# --- Refus ----------------------------------------------------------------------------------


def test_an_admin_alone_who_does_not_play_cannot_start(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    change_settings(auth_client, alice_room["code"], alice, admin_plays=False)

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.NO_PLACING_PARTICIPANT


def test_a_second_game_cannot_start_while_one_is_in_progress(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    start(auth_client, alice_room["code"], alice)

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.GAME_IN_PROGRESS
    assert db_session.scalar(select(func.count()).select_from(Game)) == 1
    assert room_events.types() == ["game.started"]


def test_a_player_cannot_start_the_game(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob)

    response: Response = start(auth_client, alice_room["code"], bob)

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.ROOM_ADMIN_REQUIRED


def test_a_user_without_a_seat_cannot_start_the_game(
    auth_client: TestClient, bob: dict[str, str], alice_room: JsonObject
):
    response: Response = start(auth_client, alice_room["code"], bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ROOM_NOT_FOUND


def test_starting_requires_authentication(auth_client: TestClient, alice_room: JsonObject):
    assert auth_client.post(f"/rooms/{alice_room['code']}/game").status_code == 401


def test_a_room_whose_template_was_purged_cannot_start(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    room: Room = db_session.scalars(select(Room).where(Room.code == alice_room["code"])).one()
    room.template_id = None
    db_session.flush()

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_NOT_FOUND


def test_a_room_whose_template_lost_its_tiles_cannot_start(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    for tile in db_session.scalars(select(Tile)):
        db_session.delete(tile)
    db_session.flush()

    response: Response = start(auth_client, alice_room["code"], alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.TEMPLATE_HAS_NO_TILES
    assert db_session.scalar(select(func.count()).select_from(Round)) == 0
    assert room_events.events == []


# --- Partie et salle ------------------------------------------------------------------------


def test_the_game_outlives_its_room(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    start(auth_client, alice_room["code"], alice)
    room: Room = db_session.scalars(select(Room).where(Room.code == alice_room["code"])).one()

    db_session.delete(room)
    db_session.flush()
    db_session.expire_all()

    game: Game = stored_game(db_session)
    assert game.room_id is None
    assert len(game.rounds) == TILE_COUNT
