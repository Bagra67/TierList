import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import PlacementPhase
from app.models.game import Game
from app.models.placement import Placement
from app.schemas.room_events import ParticipantPlacedEvent
from tests.integration.conftest import RecordingRoomEventPublisher
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


def start(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/game", headers=headers)
    assert response.status_code == 201
    return response.json()


def place(
    client: TestClient,
    code: str,
    tile_id: str,
    tier_id: str,
    position: int,
    headers: dict[str, str] | None = None,
) -> Response:
    return client.put(
        f"/rooms/{code}/game/placements/{tile_id}",
        json={"tier_id": tier_id, "position": position},
        headers=headers,
    )


def stored_game(db_session: Session) -> Game:
    return db_session.scalars(select(Game)).one()


def tile_of_round(db_session: Session, number: int) -> str:
    return str(stored_game(db_session).rounds[number - 1].snapshot_tile_id)


def next_item(client: TestClient, code: str, headers: dict[str, str]) -> None:
    # Le room admin passe à l'item suivant (#93)
    assert client.post(f"/rooms/{code}/game/next", headers=headers).status_code == 200


def seat_id(room: JsonObject, display_name: str) -> str:
    return next(
        participant["id"]
        for participant in room["participants"]
        if participant["display_name"] == display_name
    )


def board(room: JsonObject) -> list[tuple[str, str | None, int]]:
    """Plateau du lecteur : (nom du tier, texte de l'item, position), dans l'ordre renvoyé."""
    tier_names: dict[str, str] = {tier["id"]: tier["name"] for tier in room["game"]["tiers"]}
    return [
        (tier_names[placement["tier_id"]], placement["item"]["text"], placement["position"])
        for placement in room["game"]["own_placements"]
    ]


def placed_count(db_session: Session) -> int:
    """Placements dans un tier, sans les votes absents enregistrés à la fin des tours."""
    return (
        db_session.scalar(
            select(func.count())
            .select_from(Placement)
            .where(Placement.snapshot_tier_id.is_not(None))
        )
        or 0
    )


# --- Placer l'item en cours ----------------------------------------------------------------


def test_a_player_places_the_current_item(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    joined: JsonObject = auth_client.post(f"/rooms/{code}/join", headers=bob).json()
    started: JsonObject = start(auth_client, code, alice)
    tier_a: str = started["game"]["tiers"][1]["id"]

    response: Response = place(auth_client, code, tile_of_round(db_session, 1), tier_a, 0, bob)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert board(body) == [("A", "Tile 0", 0)]
    assert body["game"]["own_placements"][0]["item"]["id"] == tile_of_round(db_session, 1)
    bob_id: str = seat_id(joined, "bob")
    assert body["game"]["placed_participant_ids"] == [bob_id]
    assert body["version"] == started["version"] + 1
    placed: object = room_events.events[-1][1]
    assert isinstance(placed, ParticipantPlacedEvent)
    assert placed.room_version == body["version"]
    # Qui a placé, jamais où : ni tier ni position dans l'événement
    assert placed.data.model_dump(mode="json") == {"participant_id": bob_id, "round_number": 1}


def test_moving_the_item_in_the_same_round_replaces_the_placement(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
):
    code: str = alice_room["code"]
    started: JsonObject = start(auth_client, code, alice)
    tier_s: str = started["game"]["tiers"][0]["id"]
    tier_b: str = started["game"]["tiers"][2]["id"]
    tile: str = tile_of_round(db_session, 1)
    first: JsonObject = place(auth_client, code, tile, tier_s, 0, alice).json()
    event_count: int = len(room_events.events)

    response: Response = place(auth_client, code, tile, tier_b, 0, alice)

    assert response.status_code == 200
    body: JsonObject = response.json()
    assert board(body) == [("B", "Tile 0", 0)]
    assert placed_count(db_session) == 1
    # Les autres n'en voient rien : ni nouvelle version, ni événement
    assert body["version"] == first["version"]
    assert len(room_events.events) == event_count


def test_positions_stay_continuous_and_past_items_keep_their_order(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    started: JsonObject = start(auth_client, code, alice)
    tier_s: str = started["game"]["tiers"][0]["id"]
    tier_a: str = started["game"]["tiers"][1]["id"]
    place(auth_client, code, tile_of_round(db_session, 1), tier_s, 0, alice)

    next_item(auth_client, code, alice)
    # Avant l'item déjà placé
    before: JsonObject = place(
        auth_client, code, tile_of_round(db_session, 2), tier_s, 0, alice
    ).json()
    assert board(before) == [("S", "Tile 1", 0), ("S", "Tile 0", 1)]

    next_item(auth_client, code, alice)
    # Entre les deux
    between: JsonObject = place(
        auth_client, code, tile_of_round(db_session, 3), tier_s, 1, alice
    ).json()
    assert board(between) == [("S", "Tile 1", 0), ("S", "Tile 2", 1), ("S", "Tile 0", 2)]

    # Déplacé dans un autre tier, au-delà de la fin : il y va en dernier, et son ancien tier se
    # referme sans changer l'ordre des items passés
    moved: JsonObject = place(
        auth_client, code, tile_of_round(db_session, 3), tier_a, 99, alice
    ).json()
    assert board(moved) == [("S", "Tile 1", 0), ("S", "Tile 0", 1), ("A", "Tile 2", 0)]


def test_other_participants_never_see_where_someone_placed(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    auth_client.post(f"/rooms/{code}/join", headers=bob)
    started: JsonObject = start(auth_client, code, alice)
    placed: JsonObject = place(
        auth_client, code, tile_of_round(db_session, 1), started["game"]["tiers"][0]["id"], 0, alice
    ).json()

    seen_by_bob: JsonObject = auth_client.get(f"/rooms/{code}", headers=bob).json()

    assert seen_by_bob["game"]["own_placements"] == []
    assert seen_by_bob["game"]["placed_participant_ids"] == [seat_id(placed, "alice")]


def test_a_guest_places_with_their_cookie_and_finds_their_board_again(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    # Le cookie de l'invité reste dans le client ; les requêtes d'Alice passent son token
    assert auth_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"}).status_code == 201
    started: JsonObject = start(auth_client, code, alice)

    response: Response = place(
        auth_client, code, tile_of_round(db_session, 1), started["game"]["tiers"][0]["id"], 0
    )

    assert response.status_code == 200
    assert board(response.json()) == [("S", "Tile 0", 0)]
    assert board(auth_client.get(f"/rooms/{code}").json()) == [("S", "Tile 0", 0)]


# --- Refus ---------------------------------------------------------------------------------


def test_only_the_current_item_can_be_placed(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    tier_s: str = start(auth_client, code, alice)["game"]["tiers"][0]["id"]
    next_item(auth_client, code, alice)

    for number in (1, 3):
        response: Response = place(
            auth_client, code, tile_of_round(db_session, number), tier_s, 0, alice
        )
        assert response.status_code == 409
        assert response.json()["code"] == ErrorCode.ITEM_NOT_CURRENT
    assert placed_count(db_session) == 0


def test_a_tier_outside_the_game_is_refused(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    start(auth_client, code, alice)

    response: Response = place(
        auth_client, code, tile_of_round(db_session, 1), str(uuid.uuid4()), 0, alice
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.TIER_NOT_FOUND


def test_placing_without_a_game_is_refused(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
):
    response: Response = place(
        auth_client, alice_room["code"], str(uuid.uuid4()), str(uuid.uuid4()), 0, alice
    )

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ROUND_NOT_IN_PROGRESS


def test_the_admin_who_does_not_play_cannot_place(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    auth_client.patch(f"/rooms/{code}/settings", json={"admin_plays": False}, headers=alice)
    auth_client.post(f"/rooms/{code}/join", headers=bob)
    started: JsonObject = start(auth_client, code, alice)

    response: Response = place(
        auth_client, code, tile_of_round(db_session, 1), started["game"]["tiers"][0]["id"], 0, alice
    )

    assert response.status_code == 403
    assert response.json()["code"] == ErrorCode.NOT_A_PLACING_PARTICIPANT
    assert started["game"]["own_placements"] == []


def test_placing_needs_a_seat_and_a_valid_session(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    tier_s: str = start(auth_client, code, alice)["game"]["tiers"][0]["id"]
    tile: str = tile_of_round(db_session, 1)
    carol: dict[str, str] = register(auth_client, "carol@example.com")

    without_seat: Response = place(auth_client, code, tile, tier_s, 0, carol)
    expired: Response = place(auth_client, code, tile, tier_s, 0, {"Authorization": "Bearer x"})

    assert without_seat.status_code == 404
    assert without_seat.json()["code"] == ErrorCode.ROOM_NOT_FOUND
    assert expired.status_code == 401


def test_a_negative_position_is_refused(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    tier_s: str = start(auth_client, code, alice)["game"]["tiers"][0]["id"]

    response: Response = place(auth_client, code, tile_of_round(db_session, 1), tier_s, -1, alice)

    assert response.status_code == 422


# --- Retrait et contraintes ------------------------------------------------------------------


def test_removing_a_player_deletes_their_placements(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
):
    code: str = alice_room["code"]
    joined: JsonObject = auth_client.post(f"/rooms/{code}/join", headers=bob).json()
    started: JsonObject = start(auth_client, code, alice)
    tier_s: str = started["game"]["tiers"][0]["id"]
    place(auth_client, code, tile_of_round(db_session, 1), tier_s, 0, bob)

    response: Response = auth_client.delete(
        f"/rooms/{code}/participants/{seat_id(joined, 'bob')}", headers=alice
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert placed_count(db_session) == 0


def test_the_database_keeps_one_placement_per_tile_and_a_tier_with_its_position(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    code: str = alice_room["code"]
    started: JsonObject = start(auth_client, code, alice)
    tier_s: uuid.UUID = uuid.UUID(started["game"]["tiers"][0]["id"])
    place(auth_client, code, tile_of_round(db_session, 1), str(tier_s), 0, alice)
    game: Game = stored_game(db_session)
    placed: Placement = game.placements[0]

    duplicate: Placement = Placement(
        game_id=game.id,
        participant_id=placed.participant_id,
        snapshot_tile_id=placed.snapshot_tile_id,
        phase=PlacementPhase.ROUND,
        snapshot_tier_id=tier_s,
        position=1,
    )
    without_position: Placement = Placement(
        game_id=game.id,
        participant_id=placed.participant_id,
        snapshot_tile_id=game.rounds[1].snapshot_tile_id,
        phase=PlacementPhase.ROUND,
        snapshot_tier_id=tier_s,
        position=None,
    )
    for refused in (duplicate, without_position):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.add(refused)
            db_session.flush()
