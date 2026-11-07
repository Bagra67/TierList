import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.reports import REPORT_COOKIE
from app.core.security import hash_guest_token
from app.models.enums import ModerationTargetType, ReportReason, ReportStatus
from app.models.game import Game
from app.models.image import Image, ImageStatus
from app.models.report import Report
from app.models.snapshot_tile import SnapshotTile
from app.models.user import User
from tests.integration.helpers import (
    JsonObject,
    create_room,
    create_template,
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
    template_id: str = create_template(auth_client, db_session, alice, tile_count=2)
    room: JsonObject = create_room(auth_client, alice, template_id)
    assert auth_client.post(f"/rooms/{room['code']}/join", headers=bob).status_code == 200
    guest: Response = auth_client.post(f"/rooms/{room['code']}/guests", json={"nickname": "Lou"})
    assert guest.status_code == 201
    auth_client.cookies.clear()
    return auth_client.get(f"/rooms/{room['code']}", headers=alice).json()


@pytest.fixture
def closed_results(
    auth_client: TestClient, alice: dict[str, str], alice_room: JsonObject
) -> JsonObject:
    code: str = alice_room["code"]
    start_game(auth_client, code, alice)
    closed: JsonObject = play_and_close(auth_client, code, alice)
    token: str = closed["past_games"][0]["public_token"]
    return auth_client.get(f"/results/{token}").json()


@pytest.fixture
def image_item_id(auth_client: TestClient, db_session: Session, closed_results: JsonObject) -> str:
    image: Image = add_image(db_session, "tile-1.webp")
    tile: SnapshotTile = db_session.scalars(
        select(SnapshotTile).where(SnapshotTile.text == "Tile 1")
    ).one()
    tile.image = image
    db_session.flush()
    return str(tile.id)


def add_image(db_session: Session, storage_key: str) -> Image:
    owner: User = db_session.scalars(select(User).where(User.email == "alice@example.com")).one()
    image: Image = Image(
        owner_id=owner.id,
        storage_key=storage_key,
        width=512,
        height=512,
        size_bytes=4,
        sha256="0" * 64,
    )
    db_session.add(image)
    db_session.flush()
    return image


def send_report(
    client: TestClient,
    target_kind: str,
    target_id: str,
    headers: dict[str, str] | None = None,
    reason: str = "spam",
    details: str | None = None,
) -> Response:
    return client.post(
        "/reports",
        json={
            "target_kind": target_kind,
            "target_id": target_id,
            "reason": reason,
            "details": details,
        },
        headers=headers,
    )


def stored_reports(db_session: Session) -> list[Report]:
    return list(db_session.scalars(select(Report).order_by(Report.created_at)).all())


def participant_named(room: JsonObject, name: str) -> str:
    return next(p["id"] for p in room["participants"] if p["display_name"] == name)


def player_named(results: JsonObject, name: str) -> str:
    return next(p["id"] for p in results["players"] if p["display_name"] == name)


def test_an_account_reports_a_closed_game(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    closed_results: JsonObject,
):
    response: Response = send_report(
        auth_client, "game", closed_results["game_id"], bob, "harassment", "  Insults  "
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id"}
    assert REPORT_COOKIE not in auth_client.cookies
    report: Report = stored_reports(db_session)[0]
    alice_user: User = db_session.scalars(
        select(User).where(User.email == "alice@example.com")
    ).one()
    bob_user: User = db_session.scalars(select(User).where(User.email == "bob@example.com")).one()
    assert (report.target_type, str(report.target_id), report.target_label) == (
        ModerationTargetType.GAME,
        closed_results["game_id"],
        "Food",
    )
    assert (report.reporter_id, report.reporter_browser_hash, report.owner_id) == (
        bob_user.id,
        None,
        alice_user.id,
    )
    assert (report.reason, report.details, report.status) == (
        ReportReason.HARASSMENT,
        "Insults",
        ReportStatus.OPEN,
    )


def test_a_visitor_gets_a_cookie_whose_token_is_never_stored_in_clear(
    auth_client: TestClient, db_session: Session, closed_results: JsonObject
):
    auth_client.cookies.clear()

    response: Response = send_report(auth_client, "game", closed_results["game_id"])

    assert response.status_code == 201
    token: str = response.cookies[REPORT_COOKIE]
    set_cookie: str = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/reports" in set_cookie
    report: Report = stored_reports(db_session)[0]
    assert report.reporter_id is None
    assert report.reporter_browser_hash == hash_guest_token(token)
    assert report.reporter_browser_hash != token


def test_a_visitor_who_already_has_the_cookie_keeps_it(
    auth_client: TestClient, closed_results: JsonObject, alice_room: JsonObject
):
    auth_client.cookies.clear()
    assert send_report(auth_client, "game", closed_results["game_id"]).status_code == 201

    second: Response = send_report(
        auth_client, "participant", participant_named(alice_room, "alice")
    )

    assert second.status_code == 201
    assert "set-cookie" not in second.headers


def test_an_invalid_account_token_is_refused(auth_client: TestClient, closed_results: JsonObject):
    response: Response = send_report(
        auth_client,
        "game",
        closed_results["game_id"],
        {"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_the_same_account_cannot_report_the_same_content_twice_while_it_is_open(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], closed_results: JsonObject
):
    assert send_report(auth_client, "game", closed_results["game_id"], bob).status_code == 201

    second: Response = send_report(auth_client, "game", closed_results["game_id"], bob)

    assert second.status_code == 409
    assert second.json()["code"] == ErrorCode.REPORT_ALREADY_OPEN
    assert len(stored_reports(db_session)) == 1


def test_the_same_browser_cannot_report_the_same_content_twice_while_it_is_open(
    auth_client: TestClient, db_session: Session, closed_results: JsonObject
):
    auth_client.cookies.clear()
    assert send_report(auth_client, "game", closed_results["game_id"]).status_code == 201

    second: Response = send_report(auth_client, "game", closed_results["game_id"])

    assert second.status_code == 409
    assert second.json()["code"] == ErrorCode.REPORT_ALREADY_OPEN
    assert len(stored_reports(db_session)) == 1


def test_different_reporters_report_the_same_content(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    closed_results: JsonObject,
):
    game_id: str = closed_results["game_id"]
    auth_client.cookies.clear()

    assert send_report(auth_client, "game", game_id, alice).status_code == 201
    assert send_report(auth_client, "game", game_id, bob).status_code == 201
    assert send_report(auth_client, "game", game_id).status_code == 201
    auth_client.cookies.clear()
    assert send_report(auth_client, "game", game_id).status_code == 201

    assert len(stored_reports(db_session)) == 4


def test_a_closed_report_lets_the_same_reporter_report_again(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], closed_results: JsonObject
):
    assert send_report(auth_client, "game", closed_results["game_id"], bob).status_code == 201
    stored_reports(db_session)[0].status = ReportStatus.DISMISSED
    db_session.flush()

    second: Response = send_report(auth_client, "game", closed_results["game_id"], bob)

    assert second.status_code == 201


def test_the_reason_other_needs_details(
    auth_client: TestClient, bob: dict[str, str], closed_results: JsonObject
):
    for details in (None, "   "):
        response: Response = send_report(
            auth_client, "game", closed_results["game_id"], bob, "other", details
        )

        assert response.status_code == 422
        assert response.json()["code"] == ErrorCode.REPORT_DETAILS_REQUIRED


def test_too_long_details_are_refused(
    auth_client: TestClient, bob: dict[str, str], closed_results: JsonObject
):
    response: Response = send_report(
        auth_client, "game", closed_results["game_id"], bob, "spam", "x" * 501
    )

    assert response.status_code == 422


def test_the_limit_counts_the_reports_of_an_account(
    auth_client: TestClient,
    override_settings: Callable[..., None],
    bob: dict[str, str],
    closed_results: JsonObject,
    alice_room: JsonObject,
):
    override_settings(reports_per_hour_max=1)
    assert send_report(auth_client, "game", closed_results["game_id"], bob).status_code == 201

    response: Response = send_report(
        auth_client, "participant", participant_named(alice_room, "alice"), bob
    )

    assert response.status_code == 429
    assert response.json()["code"] == ErrorCode.REPORT_LIMIT_REACHED
    assert response.json()["params"] == {"max_reports": 1}


def test_the_limit_counts_the_reports_of_a_browser_and_not_of_another(
    auth_client: TestClient,
    override_settings: Callable[..., None],
    closed_results: JsonObject,
    alice_room: JsonObject,
):
    override_settings(reports_per_hour_max=1)
    auth_client.cookies.clear()
    assert send_report(auth_client, "game", closed_results["game_id"]).status_code == 201
    alice_id: str = participant_named(alice_room, "alice")

    limited: Response = send_report(auth_client, "participant", alice_id)
    auth_client.cookies.clear()
    other_browser: Response = send_report(auth_client, "participant", alice_id)

    assert limited.status_code == 429
    assert limited.json()["code"] == ErrorCode.REPORT_LIMIT_REACHED
    assert other_browser.status_code == 201


def test_a_refused_report_gives_no_cookie_to_a_visitor(auth_client: TestClient):
    auth_client.cookies.clear()

    response: Response = send_report(auth_client, "game", str(uuid.uuid4()))

    assert response.status_code == 404
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("target_kind", ["item", "participant", "player", "game"])
def test_an_unknown_target_is_not_found(
    auth_client: TestClient, bob: dict[str, str], target_kind: str
):
    response: Response = send_report(auth_client, target_kind, str(uuid.uuid4()), bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.REPORT_TARGET_NOT_FOUND


def test_a_game_still_in_progress_cannot_be_reported(
    auth_client: TestClient, db_session: Session, alice: dict[str, str], alice_room: JsonObject
):
    start_game(auth_client, alice_room["code"], alice)
    game: Game = db_session.scalars(select(Game)).one()

    response: Response = send_report(auth_client, "game", str(game.id), alice)

    assert response.status_code == 404
    assert stored_reports(db_session) == []


def test_an_item_without_image_cannot_be_reported(
    auth_client: TestClient, bob: dict[str, str], closed_results: JsonObject
):
    item_id: str = closed_results["items"][0]["id"]

    response: Response = send_report(auth_client, "item", item_id, bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.REPORT_TARGET_NOT_FOUND


@pytest.mark.parametrize("status", [ImageStatus.HIDDEN, ImageStatus.DELETED])
def test_an_image_already_removed_cannot_be_reported(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    image_item_id: str,
    status: ImageStatus,
):
    image: Image = db_session.scalars(select(Image)).one()
    image.status = status
    db_session.flush()

    response: Response = send_report(auth_client, "item", image_item_id, bob)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.REPORT_TARGET_NOT_FOUND


def test_the_same_image_is_one_target_from_one_game_to_another(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    image_item_id: str,
):
    image: Image = db_session.scalars(select(Image)).one()
    other_tile: SnapshotTile = db_session.scalars(
        select(SnapshotTile).where(SnapshotTile.text == "Tile 0")
    ).one()
    other_tile.image = image
    db_session.flush()

    assert send_report(auth_client, "item", image_item_id, bob).status_code == 201
    second: Response = send_report(auth_client, "item", str(other_tile.id), bob)

    assert second.status_code == 409
    report: Report = stored_reports(db_session)[0]
    assert (report.target_type, report.target_id, report.target_label, report.owner_id) == (
        ModerationTargetType.IMAGE,
        image.id,
        None,
        image.owner_id,
    )


def test_the_nickname_of_an_account_is_one_target_from_the_room_to_the_results(
    auth_client: TestClient,
    db_session: Session,
    bob: dict[str, str],
    alice_room: JsonObject,
    closed_results: JsonObject,
):
    alice_user: User = db_session.scalars(
        select(User).where(User.email == "alice@example.com")
    ).one()
    from_room: Response = send_report(
        auth_client, "participant", participant_named(alice_room, "alice"), bob
    )

    from_results: Response = send_report(
        auth_client, "player", player_named(closed_results, "alice"), bob
    )

    assert from_room.status_code == 201
    assert from_results.status_code == 409
    report: Report = stored_reports(db_session)[0]
    assert (report.target_type, report.target_id, report.target_label, report.owner_id) == (
        ModerationTargetType.NICKNAME,
        alice_user.id,
        "alice",
        alice_user.id,
    )


def test_the_nickname_of_a_guest_has_no_owner(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], alice_room: JsonObject
):
    guest_id: str = participant_named(alice_room, "Lou")

    response: Response = send_report(auth_client, "participant", guest_id, bob)

    assert response.status_code == 201
    report: Report = stored_reports(db_session)[0]
    assert (str(report.target_id), report.target_label, report.owner_id) == (guest_id, "Lou", None)


def test_the_nickname_of_a_guest_player_has_no_owner(
    auth_client: TestClient, db_session: Session, bob: dict[str, str], closed_results: JsonObject
):
    player_id: str = player_named(closed_results, "Lou")

    response: Response = send_report(auth_client, "player", player_id, bob)

    assert response.status_code == 201
    report: Report = stored_reports(db_session)[0]
    assert (str(report.target_id), report.target_label, report.owner_id) == (player_id, "Lou", None)


def test_a_report_survives_the_deletion_of_the_accounts(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    bob: dict[str, str],
    closed_results: JsonObject,
):
    assert send_report(auth_client, "game", closed_results["game_id"], bob).status_code == 201

    for user in db_session.scalars(select(User)).all():
        db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    report: Report = stored_reports(db_session)[0]
    assert (report.reporter_id, report.owner_id) == (None, None)
    assert report.target_label == "Food"


def test_no_response_says_who_reported(
    auth_client: TestClient,
    alice: dict[str, str],
    bob: dict[str, str],
    closed_results: JsonObject,
):
    assert send_report(auth_client, "game", closed_results["game_id"], bob).status_code == 201
    bob_id: str = auth_client.get("/auth/me", headers=bob).json()["id"]

    seen_by_owner: Response = auth_client.get("/auth/me", headers=alice)
    history: Response = auth_client.get("/history", headers=alice)

    assert bob_id not in seen_by_owner.text
    assert bob_id not in history.text
