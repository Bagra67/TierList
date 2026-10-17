"""Clôture et sauvegarde d'une partie (US-5.1) : à la fin du cooldown, les joueurs sont figés et
la partie ne dépend plus des places de la salle."""

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
from app.models.game_player import GamePlayer
from app.models.placement import Placement
from app.models.user import User
from tests.integration.helpers import (
    PASSWORD,
    JsonObject,
    create_room,
    create_template,
    next_item,
    place,
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
def alice_room(auth_client: TestClient, db_session: Session, alice: dict[str, str]) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice, tile_count=TILE_COUNT)
    return create_room(auth_client, alice, template_id)


def place_current_in_first_tier(
    client: TestClient, room: JsonObject, headers: dict[str, str] | None = None
) -> None:
    game: JsonObject = room["game"]
    response: Response = place(
        client, room["code"], game["current_item"]["id"], game["tiers"][0]["id"], 0, headers
    )
    assert response.status_code == 200


def play_and_close(client: TestClient, code: str, alice: dict[str, str]) -> JsonObject:
    """Termine les tours restants, puis le cooldown (« Terminer maintenant »)."""
    room: JsonObject = client.get(f"/rooms/{code}", headers=alice).json()
    while room["game"]["status"] == "in_round":
        room = next_item(client, code, alice)
    response: Response = client.post(f"/rooms/{code}/game/end", headers=alice)
    assert response.status_code == 200
    return response.json()


def stored_game(db_session: Session) -> Game:
    game: Game = db_session.scalars(select(Game)).one()
    db_session.refresh(game)
    return game


def user_id(db_session: Session, email: str) -> uuid.UUID:
    return db_session.scalars(select(User.id).where(User.email == email)).one()


def players(db_session: Session) -> list[tuple[str, uuid.UUID | None]]:
    """Les joueurs figés : (nom, compte), par nom."""
    return sorted(
        (player.display_name, player.user_id) for player in db_session.scalars(select(GamePlayer))
    )


def placement_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Placement)) or 0


@pytest.fixture
def closed_game(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    alice_room: JsonObject,
) -> JsonObject:
    """Alice, Bob et l'invitée Lou jouent ; Alice et Bob placent le premier item, Lou rien ; le
    room admin termine le cooldown."""
    code: str = alice_room["code"]
    auth_client.post(f"/rooms/{code}/join", headers=bob)
    assert auth_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"}).status_code == 201
    started: JsonObject = start_game(auth_client, code, alice)
    place_current_in_first_tier(auth_client, started, alice)
    place_current_in_first_tier(auth_client, started, bob)
    return play_and_close(auth_client, code, alice)


def test_closing_freezes_every_player_and_their_placements(
    db_session: Session, closed_game: JsonObject
):
    assert players(db_session) == [
        ("Lou", None),
        ("alice", user_id(db_session, "alice@example.com")),
        ("bob", user_id(db_session, "bob@example.com")),
    ]
    game: Game = stored_game(db_session)
    # Les placements de tour (votes absents compris) et finaux passent tous aux joueurs figés
    assert game.placements
    assert all(
        placement.participant_id is None and placement.player_id is not None
        for placement in game.placements
    )
    lou: GamePlayer = next(player for player in game.players if player.display_name == "Lou")
    assert [placement.is_absent for placement in game.placements if placement.player is lou] == [
        True,
        True,
    ]


def test_the_admin_who_does_not_play_is_not_a_player(
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

    play_and_close(auth_client, code, alice)

    assert [name for name, _ in players(db_session)] == ["bob"]


def test_removing_a_seat_after_closing_keeps_the_ranking(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    closed_game: JsonObject,
):
    count: int = placement_count(db_session)
    bob_id: str = next(p["id"] for p in closed_game["participants"] if p["display_name"] == "bob")

    removed: Response = auth_client.delete(
        f"/rooms/{closed_game['code']}/participants/{bob_id}", headers=alice
    )

    assert removed.status_code == 200
    assert placement_count(db_session) == count
    assert "bob" in [name for name, _ in players(db_session)]


def test_deleting_an_account_keeps_the_closed_game(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    closed_game: JsonObject,
):
    count: int = placement_count(db_session)

    deleted: Response = auth_client.request(
        "DELETE", "/auth/me", json={"password": PASSWORD}, headers=bob
    )

    assert deleted.status_code == 204
    assert placement_count(db_session) == count
    # Le joueur reste dans la partie, sans compte : la partie n'est plus dans un historique
    assert ("bob", None) in players(db_session)


def test_a_closed_game_no_longer_changes(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    closed_game: JsonObject,
):
    game: Game = stored_game(db_session)
    tile_id: str = str(game.rounds[0].snapshot_tile_id)
    tier_id: str = str(game.snapshot.tiers[0].id)

    response: Response = place(auth_client, closed_game["code"], tile_id, tier_id, 0, alice)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ROUND_NOT_IN_PROGRESS


def test_a_new_game_starts_after_a_closed_one(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    closed_game: JsonObject,
):
    started: JsonObject = start_game(auth_client, closed_game["code"], alice)

    place_current_in_first_tier(auth_client, started, alice)

    room: JsonObject = auth_client.get(f"/rooms/{closed_game['code']}", headers=alice).json()
    # Le plateau de la nouvelle partie ne contient que son propre placement
    assert len(room["game"]["own_placements"]) == 1
    assert db_session.scalar(select(func.count()).select_from(Game)) == 2


def test_a_placement_belongs_to_a_seat_or_a_player(db_session: Session, closed_game: JsonObject):
    game: Game = stored_game(db_session)
    orphan: Placement = Placement(
        game_id=game.id,
        snapshot_tile_id=game.rounds[0].snapshot_tile_id,
        phase=PlacementPhase.ROUND,
    )
    db_session.add(orphan)

    with pytest.raises(IntegrityError):
        db_session.flush()
