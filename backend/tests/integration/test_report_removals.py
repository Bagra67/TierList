import uuid

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.enums import ModerationActionKind, ModerationTargetType, ReportStatus
from app.models.game import Game
from app.models.moderation_action import ModerationAction
from app.models.participant import Participant
from app.models.report import Report
from app.models.room import Room
from app.models.user import User
from tests.integration.helpers import (
    JsonObject,
    create_room,
    create_template,
    play_and_close,
    register,
    register_super_admin,
    start_game,
)

pytestmark = pytest.mark.integration

REASON: dict[str, str] = {"reason": "Illicite"}


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


@pytest.fixture
def room_code(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], bob: dict[str, str]
) -> str:
    template_id: str = create_template(auth_client, db_session, alice, tile_count=2)
    code: str = create_room(auth_client, alice, template_id)["code"]
    assert auth_client.post(f"/rooms/{code}/join", headers=bob).status_code == 200
    guest: Response = auth_client.post(f"/rooms/{code}/guests", json={"nickname": "Lou"})
    assert guest.status_code == 201
    auth_client.cookies.clear()
    return code


@pytest.fixture
def results_token(auth_client: TestClient, alice: dict[str, str], room_code: str) -> str:
    start_game(auth_client, room_code, alice)
    closed: JsonObject = play_and_close(auth_client, room_code, alice)
    return closed["past_games"][0]["public_token"]


def results_of(client: TestClient, token: str) -> JsonObject:
    response: Response = client.get(f"/results/{token}")
    assert response.status_code == 200
    return response.json()


def player_names(results: JsonObject) -> set[str]:
    return {player["display_name"] for player in results["players"]}


def player_named(results: JsonObject, name: str) -> str:
    return next(player["id"] for player in results["players"] if player["display_name"] == name)


def lobby_names(client: TestClient, code: str, headers: dict[str, str]) -> set[str]:
    room: JsonObject = client.get(f"/rooms/{code}", headers=headers).json()
    return {participant["display_name"] for participant in room["participants"]}


def guest_named(db_session: Session, name: str) -> Participant:
    return db_session.scalars(select(Participant).where(Participant.nickname == name)).one()


def add_report(
    db_session: Session, target_type: ModerationTargetType, target_id: uuid.UUID
) -> Report:
    report: Report = Report(
        reporter_browser_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        target_type=target_type,
        target_id=target_id,
        reason="spam",
    )
    db_session.add(report)
    db_session.flush()
    return report


def remove_nickname(client: TestClient, headers: dict[str, str], target_id: object) -> Response:
    return client.post(
        "/moderation/nicknames/remove",
        json={"target_id": str(target_id), **REASON},
        headers=headers,
    )


def moderate_game(
    client: TestClient, headers: dict[str, str], game_id: object, action: str
) -> Response:
    return client.post(f"/moderation/games/{game_id}/{action}", json=REASON, headers=headers)


def only_game(db_session: Session) -> Game:
    return db_session.scalars(select(Game)).one()


def log_entries(db_session: Session) -> list[ModerationAction]:
    return list(db_session.scalars(select(ModerationAction).order_by(ModerationAction.created_at)))


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/moderation/nicknames/remove"),
        ("POST", f"/moderation/games/{uuid.uuid4()}/hide"),
        ("POST", f"/moderation/games/{uuid.uuid4()}/unhide"),
        ("GET", "/moderation/games/hidden"),
    ],
)
def test_removal_and_hiding_refuse_visitors_and_other_accounts(
    auth_client: TestClient, bob: dict[str, str], method: str, path: str
):
    body: JsonObject | None = (
        {"target_id": str(uuid.uuid4()), **REASON} if method == "POST" else None
    )

    without_session: Response = auth_client.request(method, path, json=body)
    with_account: Response = auth_client.request(method, path, json=body, headers=bob)

    assert without_session.status_code == 401
    assert with_account.status_code == 403


def test_removing_the_nickname_of_an_account_replaces_it_everywhere(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
    room_code: str,
    results_token: str,
):
    bob_user: User = db_session.scalars(select(User).where(User.email == "bob@example.com")).one()
    report: Report = add_report(db_session, ModerationTargetType.NICKNAME, bob_user.id)
    other: Report = add_report(db_session, ModerationTargetType.NICKNAME, uuid.uuid4())

    response: Response = remove_nickname(auth_client, nina, bob_user.id)

    assert response.status_code == 204
    db_session.expire_all()
    replacement: str = bob_user.display_name
    assert replacement.startswith("#")
    assert replacement in player_names(results_of(auth_client, results_token))
    assert "bob" not in player_names(results_of(auth_client, results_token))
    assert lobby_names(auth_client, room_code, alice) == {"alice", replacement, "Lou"}
    entry: ModerationAction = log_entries(db_session)[0]
    assert (entry.action, entry.target_type, entry.target_label) == (
        ModerationActionKind.DELETE,
        ModerationTargetType.NICKNAME,
        "bob",
    )
    assert report.status == ReportStatus.ACTIONED
    assert report.closed_by_action_id == entry.id
    assert other.status == ReportStatus.OPEN


def test_removing_the_nickname_of_a_guest_from_the_room_reaches_the_results(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    room_code: str,
    results_token: str,
):
    guest: Participant = guest_named(db_session, "Lou")
    player_id: str = player_named(results_of(auth_client, results_token), "Lou")
    on_participant: Report = add_report(db_session, ModerationTargetType.NICKNAME, guest.id)
    on_player: Report = add_report(db_session, ModerationTargetType.NICKNAME, uuid.UUID(player_id))

    response: Response = remove_nickname(auth_client, nina, guest.id)

    assert response.status_code == 204
    db_session.expire_all()
    replacement: str | None = guest.nickname
    assert replacement is not None
    assert replacement.startswith("#")
    assert replacement in player_names(results_of(auth_client, results_token))
    assert replacement in lobby_names(auth_client, room_code, alice)
    assert log_entries(db_session)[0].target_label == "Lou"
    assert on_participant.status == ReportStatus.ACTIONED
    assert on_player.status == ReportStatus.ACTIONED


def test_removing_the_nickname_of_a_guest_from_the_results_reaches_the_room(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    room_code: str,
    results_token: str,
):
    guest: Participant = guest_named(db_session, "Lou")
    player_id: str = player_named(results_of(auth_client, results_token), "Lou")

    response: Response = remove_nickname(auth_client, nina, player_id)

    assert response.status_code == 204
    db_session.expire_all()
    replacement: str | None = guest.nickname
    assert replacement is not None
    assert replacement in player_names(results_of(auth_client, results_token))
    assert replacement in lobby_names(auth_client, room_code, alice)


def test_removing_the_nickname_of_a_guest_whose_room_is_gone_changes_their_player(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    room_code: str,
    results_token: str,
):
    player_id: str = player_named(results_of(auth_client, results_token), "Lou")
    room: Room = db_session.scalars(select(Room).where(Room.code == room_code)).one()
    db_session.delete(room)
    db_session.flush()
    db_session.expire_all()

    response: Response = remove_nickname(auth_client, nina, player_id)

    assert response.status_code == 204
    names: set[str] = player_names(results_of(auth_client, results_token))
    assert "Lou" not in names
    assert any(name.startswith("#") for name in names)


def test_two_guests_of_a_room_can_lose_their_nickname(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], room_code: str
):
    other: Response = auth_client.post(f"/rooms/{room_code}/guests", json={"nickname": "Max"})
    assert other.status_code == 201
    auth_client.cookies.clear()
    lou: Participant = guest_named(db_session, "Lou")
    max_guest: Participant = guest_named(db_session, "Max")

    assert remove_nickname(auth_client, nina, lou.id).status_code == 204
    assert remove_nickname(auth_client, nina, max_guest.id).status_code == 204

    db_session.expire_all()
    assert lou.nickname != max_guest.nickname


def test_removing_an_unknown_nickname_is_not_found(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    response: Response = remove_nickname(auth_client, nina, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.NICKNAME_NOT_FOUND
    assert log_entries(db_session) == []


def test_hiding_a_game_closes_its_results_and_its_reports(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    bob: dict[str, str],
    results_token: str,
):
    game: Game = only_game(db_session)
    report: Report = add_report(db_session, ModerationTargetType.GAME, game.id)

    response: Response = moderate_game(auth_client, nina, game.id, "hide")

    assert response.status_code == 204
    assert (
        auth_client.get(f"/results/{results_token}").json()["code"] == ErrorCode.RESULTS_NOT_FOUND
    )
    hidden: JsonObject = auth_client.get("/moderation/games/hidden", headers=nina).json()
    assert [hidden_game["id"] for hidden_game in hidden["games"]] == [str(game.id)]
    assert hidden["games"][0]["template_name"] == "Food"
    db_session.expire_all()
    entry: ModerationAction = log_entries(db_session)[0]
    assert (entry.action, entry.target_type, entry.target_label) == (
        ModerationActionKind.HIDE,
        ModerationTargetType.GAME,
        "Food",
    )
    assert report.status == ReportStatus.ACTIONED
    new_report: Response = auth_client.post(
        "/reports",
        json={"target_kind": "game", "target_id": str(game.id), "reason": "spam"},
        headers=bob,
    )
    assert new_report.status_code == 404


def test_unhiding_a_game_shows_its_results_again(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], results_token: str
):
    game: Game = only_game(db_session)
    assert moderate_game(auth_client, nina, game.id, "hide").status_code == 204

    response: Response = moderate_game(auth_client, nina, game.id, "unhide")

    assert response.status_code == 204
    assert results_of(auth_client, results_token)["game_id"] == str(game.id)
    assert auth_client.get("/moderation/games/hidden", headers=nina).json()["games"] == []
    assert [entry.action for entry in log_entries(db_session)] == [
        ModerationActionKind.HIDE,
        ModerationActionKind.UNHIDE,
    ]


def test_a_game_cannot_be_hidden_twice_nor_unhidden_when_visible(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], results_token: str
):
    game: Game = only_game(db_session)

    unhide: Response = moderate_game(auth_client, nina, game.id, "unhide")
    assert moderate_game(auth_client, nina, game.id, "hide").status_code == 204
    second_hide: Response = moderate_game(auth_client, nina, game.id, "hide")

    assert unhide.status_code == 409
    assert second_hide.status_code == 409
    assert second_hide.json()["code"] == ErrorCode.GAME_MODERATION_CONFLICT


def test_only_a_closed_game_can_be_hidden(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    room_code: str,
):
    start_game(auth_client, room_code, alice)
    game: Game = only_game(db_session)

    in_progress: Response = moderate_game(auth_client, nina, game.id, "hide")
    unknown: Response = moderate_game(auth_client, nina, uuid.uuid4(), "hide")

    assert in_progress.status_code == 404
    assert in_progress.json()["code"] == ErrorCode.GAME_NOT_FOUND
    assert unknown.status_code == 404


def test_the_hidden_games_are_paginated_newest_first(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    room_code: str,
    results_token: str,
):
    first_game: Game = only_game(db_session)
    game_ids: list[str] = [str(first_game.id)]
    for _ in range(2):
        start_game(auth_client, room_code, alice)
        closed: JsonObject = play_and_close(auth_client, room_code, alice)
        game_ids.append(results_of(auth_client, closed["past_games"][0]["public_token"])["game_id"])
    for game_id in game_ids:
        assert moderate_game(auth_client, nina, game_id, "hide").status_code == 204

    first_page: JsonObject = auth_client.get(
        "/moderation/games/hidden", params={"limit": 2}, headers=nina
    ).json()
    second_page: JsonObject = auth_client.get(
        "/moderation/games/hidden", params={"limit": 2, "offset": 2}, headers=nina
    ).json()

    assert [game["id"] for game in first_page["games"]] == [game_ids[2], game_ids[1]]
    assert first_page["has_more"] is True
    assert [game["id"] for game in second_page["games"]] == [game_ids[0]]
    assert second_page["has_more"] is False
