import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.models.enums import (
    ModerationActionKind,
    ModerationTargetType,
    ReportReason,
    ReportStatus,
)
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.report import Report
from app.models.user import User
from app.services.maintenance import purge_closed_reports
from tests.integration.helpers import (
    JsonObject,
    counted_queries,
    register,
    register_super_admin,
)

pytestmark = pytest.mark.integration

GROUP_QUERIES_MAX = 12


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def bob(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "bob@example.com")


def user_named(db_session: Session, name: str) -> User:
    return db_session.scalars(select(User).where(User.email == f"{name}@example.com")).one()


def add_image(db_session: Session, owner: User) -> Image:
    image: Image = Image(
        owner_id=owner.id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="a" * 64,
    )
    db_session.add(image)
    db_session.flush()
    return image


def add_report(
    db_session: Session,
    target_type: ModerationTargetType,
    target_id: uuid.UUID,
    owner: User | None = None,
    reason: ReportReason = ReportReason.SPAM,
    details: str | None = None,
    label: str | None = None,
    days_ago: float = 0,
) -> Report:
    report: Report = Report(
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
        reporter_browser_hash=uuid.uuid4().hex + uuid.uuid4().hex,
        target_type=target_type,
        target_id=target_id,
        target_label=label,
        owner_id=owner.id if owner is not None else None,
        reason=reason,
        details=details,
    )
    db_session.add(report)
    db_session.flush()
    return report


def queue(client: TestClient, headers: dict[str, str], **params: str | int) -> JsonObject:
    response: Response = client.get("/moderation/reports", params=params, headers=headers)
    assert response.status_code == 200
    return response.json()


def dismiss(
    client: TestClient, headers: dict[str, str], target_type: str, target_id: uuid.UUID
) -> Response:
    return client.post(
        "/moderation/reports/dismiss",
        json={"target_type": target_type, "target_id": str(target_id), "reason": "  Pas grave  "},
        headers=headers,
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/moderation/reports"),
        ("GET", "/moderation/reports/count"),
        ("POST", "/moderation/reports/dismiss"),
    ],
)
def test_the_queue_refuses_visitors_and_other_accounts(
    auth_client: TestClient, alice: dict[str, str], method: str, path: str
):
    body: JsonObject = {
        "target_type": "game",
        "target_id": str(uuid.uuid4()),
        "reason": "Motif",
    }
    json_body: JsonObject | None = body if method == "POST" else None

    without_session: Response = auth_client.request(method, path, json=json_body)
    with_account: Response = auth_client.request(method, path, json=json_body, headers=alice)

    assert without_session.status_code == 401
    assert with_account.status_code == 403


def test_the_reports_are_grouped_by_content_the_most_reported_first(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
):
    owner: User = user_named(db_session, "alice")
    once_id: uuid.UUID = uuid.uuid4()
    twice_id: uuid.UUID = uuid.uuid4()
    add_report(db_session, ModerationTargetType.GAME, once_id, owner, label="Épices")
    add_report(
        db_session,
        ModerationTargetType.NICKNAME,
        twice_id,
        owner,
        ReportReason.HARASSMENT,
        "Insultes",
        "alice",
        days_ago=2,
    )
    add_report(db_session, ModerationTargetType.NICKNAME, twice_id, owner, label="alice")

    body: JsonObject = queue(auth_client, nina)

    assert body["has_more"] is False
    assert [content["target_id"] for content in body["contents"]] == [str(twice_id), str(once_id)]
    first: JsonObject = body["contents"][0]
    assert first["target_type"] == "nickname"
    assert first["label"] == "alice"
    assert (first["owner_id"], first["owner_name"]) == (str(owner.id), "alice")
    assert first["report_count"] == 2
    assert sorted((reason["reason"], reason["count"]) for reason in first["reasons"]) == [
        ("harassment", 1),
        ("spam", 1),
    ]
    assert first["details"] == ["Insultes"]
    assert (first["image_url"], first["public_token"]) == (None, None)


def test_contents_equally_reported_are_shown_oldest_first(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    recent_id: uuid.UUID = uuid.uuid4()
    old_id: uuid.UUID = uuid.uuid4()
    add_report(db_session, ModerationTargetType.GAME, recent_id, days_ago=1)
    add_report(db_session, ModerationTargetType.GAME, old_id, days_ago=5)

    body: JsonObject = queue(auth_client, nina)

    assert [content["target_id"] for content in body["contents"]] == [str(old_id), str(recent_id)]


def test_the_pages_follow_each_other(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    target_ids: list[uuid.UUID] = [uuid.uuid4() for _ in range(3)]
    for days_ago, target_id in enumerate(reversed(target_ids)):
        add_report(db_session, ModerationTargetType.GAME, target_id, days_ago=days_ago)

    first_page: JsonObject = queue(auth_client, nina, limit=2)
    second_page: JsonObject = queue(auth_client, nina, limit=2, offset=2)

    assert [content["target_id"] for content in first_page["contents"]] == [
        str(target_ids[0]),
        str(target_ids[1]),
    ]
    assert first_page["has_more"] is True
    assert [content["target_id"] for content in second_page["contents"]] == [str(target_ids[2])]
    assert second_page["has_more"] is False


def test_the_queue_can_be_filtered_by_owner(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    bob: dict[str, str],
):
    alice_user: User = user_named(db_session, "alice")
    alice_target: uuid.UUID = uuid.uuid4()
    add_report(db_session, ModerationTargetType.GAME, alice_target, alice_user)
    add_report(db_session, ModerationTargetType.GAME, uuid.uuid4(), user_named(db_session, "bob"))

    body: JsonObject = queue(auth_client, nina, owner_id=str(alice_user.id))

    assert [content["target_id"] for content in body["contents"]] == [str(alice_target)]


def test_an_image_is_shown_with_its_address_and_a_guest_has_no_owner(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    image: Image = add_image(db_session, user_named(db_session, "alice"))
    add_report(db_session, ModerationTargetType.IMAGE, image.id, user_named(db_session, "alice"))
    add_report(db_session, ModerationTargetType.NICKNAME, uuid.uuid4(), None, label="Lou")

    contents: list[JsonObject] = queue(auth_client, nina)["contents"]

    image_content: JsonObject = next(c for c in contents if c["target_type"] == "image")
    guest_content: JsonObject = next(c for c in contents if c["target_type"] == "nickname")
    assert image.storage_key in image_content["image_url"]
    assert (guest_content["owner_id"], guest_content["owner_name"]) == (None, None)
    assert guest_content["label"] == "Lou"


def test_the_queue_never_says_who_reported(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], bob: dict[str, str]
):
    reporter: User = user_named(db_session, "bob")
    report: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    browser_hash: str | None = report.reporter_browser_hash
    other: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    other.reporter_browser_hash = None
    other.reporter_id = reporter.id
    db_session.flush()

    response: Response = auth_client.get("/moderation/reports", headers=nina)

    assert str(reporter.id) not in response.text
    assert browser_hash is not None
    assert browser_hash not in response.text


def test_the_number_of_queries_does_not_grow_with_the_page(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    owner: User = user_named(db_session, "alice")
    for _ in range(10):
        image: Image = add_image(db_session, owner)
        add_report(db_session, ModerationTargetType.IMAGE, image.id, owner)
        add_report(db_session, ModerationTargetType.GAME, uuid.uuid4(), owner)

    with counted_queries(db_session) as statements:
        queue(auth_client, nina)

    assert len(statements) <= GROUP_QUERIES_MAX


def test_the_count_gives_the_number_of_contents_with_an_open_report(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    target_id: uuid.UUID = uuid.uuid4()
    add_report(db_session, ModerationTargetType.GAME, target_id)
    add_report(db_session, ModerationTargetType.GAME, target_id)
    add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    closed: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    closed.status = ReportStatus.DISMISSED
    db_session.flush()

    response: Response = auth_client.get("/moderation/reports/count", headers=nina)

    assert response.json() == {"open_contents": 2}


def test_dismissing_closes_the_reports_of_this_content_only_and_writes_to_the_log(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    target_id: uuid.UUID = uuid.uuid4()
    other_id: uuid.UUID = uuid.uuid4()
    reports: list[Report] = [
        add_report(db_session, ModerationTargetType.GAME, target_id, label="Épices"),
        add_report(db_session, ModerationTargetType.GAME, target_id, label="Épices"),
    ]
    other: Report = add_report(db_session, ModerationTargetType.GAME, other_id)

    response: Response = dismiss(auth_client, nina, "game", target_id)

    assert response.status_code == 204
    action: ModerationAction = db_session.scalars(select(ModerationAction)).one()
    assert (action.action, action.target_type, action.target_id, action.target_label) == (
        ModerationActionKind.DISMISS,
        ModerationTargetType.GAME,
        target_id,
        "Épices",
    )
    assert action.reason == "Pas grave"
    db_session.expire_all()
    for report in reports:
        assert report.status == ReportStatus.DISMISSED
        assert report.closed_at is not None
        assert report.closed_by_action_id == action.id
    assert other.status == ReportStatus.OPEN
    assert [c["target_id"] for c in queue(auth_client, nina)["contents"]] == [str(other_id)]


def test_dismissing_a_content_without_open_report_is_not_found(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    target_id: uuid.UUID = uuid.uuid4()
    closed: Report = add_report(db_session, ModerationTargetType.GAME, target_id)
    closed.status = ReportStatus.DISMISSED
    db_session.flush()

    response: Response = dismiss(auth_client, nina, "game", target_id)

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.REPORTS_NOT_OPEN
    assert db_session.scalars(select(ModerationAction)).first() is None


def test_a_new_report_after_a_dismissal_opens_the_content_again(
    auth_client: TestClient, db_session: Session, nina: dict[str, str]
):
    target_id: uuid.UUID = uuid.uuid4()
    add_report(db_session, ModerationTargetType.GAME, target_id)
    assert dismiss(auth_client, nina, "game", target_id).status_code == 204

    add_report(db_session, ModerationTargetType.GAME, target_id)

    contents: list[JsonObject] = queue(auth_client, nina)["contents"]
    assert [(c["target_id"], c["report_count"]) for c in contents] == [(str(target_id), 1)]


@pytest.mark.parametrize("action", ["hide", "delete"])
def test_removing_an_image_closes_its_reports_wherever_it_is_decided(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
    action: str,
):
    owner: User = user_named(db_session, "alice")
    image: Image = add_image(db_session, owner)
    stored_images[image.storage_key] = b"webp"
    report: Report = add_report(db_session, ModerationTargetType.IMAGE, image.id, owner)
    other: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())

    response: Response = auth_client.post(
        f"/moderation/images/{image.id}/{action}", json={"reason": "Illicite"}, headers=nina
    )

    assert response.status_code == 204
    db_session.expire_all()
    log_entry: ModerationAction = db_session.scalars(select(ModerationAction)).one()
    assert report.status == ReportStatus.ACTIONED
    assert report.closed_by_action_id == log_entry.id
    assert other.status == ReportStatus.OPEN


def test_unhiding_an_image_does_not_touch_its_reports(
    auth_client: TestClient,
    db_session: Session,
    stored_images: dict[str, bytes],
    nina: dict[str, str],
    alice: dict[str, str],
):
    owner: User = user_named(db_session, "alice")
    image: Image = add_image(db_session, owner)
    stored_images[image.storage_key] = b"webp"
    hide: Response = auth_client.post(
        f"/moderation/images/{image.id}/hide", json={"reason": "Illicite"}, headers=nina
    )
    assert hide.status_code == 204
    report: Report = add_report(db_session, ModerationTargetType.IMAGE, image.id, owner)

    response: Response = auth_client.post(
        f"/moderation/images/{image.id}/unhide", json={"reason": "Erreur"}, headers=nina
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert report.status == ReportStatus.OPEN


def test_banning_an_account_leaves_the_reports_on_its_content_open(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    owner: User = user_named(db_session, "alice")
    report: Report = add_report(db_session, ModerationTargetType.NICKNAME, owner.id, owner)

    response: Response = auth_client.post(
        f"/moderation/accounts/{owner.id}/ban", json={"reason": "Récidive"}, headers=nina
    )

    assert response.status_code == 204
    db_session.expire_all()
    assert report.status == ReportStatus.OPEN


def test_the_purge_deletes_only_the_reports_closed_for_longer_than_the_retention(
    db_session: Session,
):
    now: datetime = datetime.now(UTC)
    old_closed: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    old_closed.status = ReportStatus.DISMISSED
    old_closed.closed_at = now - timedelta(days=366)
    recent_closed: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4())
    recent_closed.status = ReportStatus.ACTIONED
    recent_closed.closed_at = now - timedelta(days=364)
    old_open: Report = add_report(db_session, ModerationTargetType.GAME, uuid.uuid4(), days_ago=800)
    kept_ids: set[uuid.UUID] = {recent_closed.id, old_open.id}
    db_session.flush()

    purged: int = purge_closed_reports(lambda: nullcontext(db_session), get_settings())

    assert purged == 1
    assert {report.id for report in db_session.scalars(select(Report)).all()} == kept_ids


def test_closed_reports_are_kept_the_year_stated_by_the_privacy_policy():
    assert get_settings().closed_report_retention_days == 365
