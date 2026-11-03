import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app.constants.auth import REFRESH_TOKEN_COOKIE
from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.account_ban import AccountBan
from app.models.enums import ModerationActionKind, ModerationTargetType, UserRole
from app.models.moderation_action import ModerationAction
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories import users as user_repository
from app.services.account_bans import AccountBanService
from app.services.moderation_log import ModerationLogService
from tests.integration.helpers import PASSWORD, JsonObject, register, register_super_admin

pytestmark = pytest.mark.integration

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


@pytest.fixture
def nina(auth_client: TestClient, db_session: Session) -> dict[str, str]:
    return register_super_admin(auth_client, db_session, "nina@example.com")


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


def account(db_session: Session, email: str) -> User:
    return db_session.scalars(select(User).where(User.email == email)).one()


def ban(
    client: TestClient,
    headers: dict[str, str],
    user_id: uuid.UUID | str,
    ends_at: datetime | None = None,
    reason: str = "Repeated harassment",
) -> Response:
    body: JsonObject = {"reason": reason}
    if ends_at is not None:
        body["ends_at"] = ends_at.isoformat()
    return client.post(f"/moderation/accounts/{user_id}/ban", json=body, headers=headers)


def lift(
    client: TestClient, headers: dict[str, str], user_id: uuid.UUID | str, reason: str = "Appeal"
) -> Response:
    return client.post(
        f"/moderation/accounts/{user_id}/lift-ban", json={"reason": reason}, headers=headers
    )


def login(client: TestClient, email: str) -> Response:
    client.cookies.clear()
    return client.post("/auth/login", json={"email": email, "password": PASSWORD})


def bans_of(db_session: Session, user: User) -> list[AccountBan]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(AccountBan).where(AccountBan.user_id == user.id).order_by(AccountBan.created_at)
        ).all()
    )


def test_a_temporary_ban_signs_the_account_out_and_refuses_its_sign_in_until_the_end(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ends_at: datetime = datetime.now(UTC) + timedelta(days=7)

    response: Response = ban(auth_client, nina, alice_account.id, ends_at, "  Spam  ")

    assert response.status_code == 204
    assert auth_client.get("/auth/me", headers=alice).status_code == 401
    assert auth_client.post("/auth/refresh").status_code == 401
    refused: Response = login(auth_client, "alice@example.com")
    assert refused.status_code == 403
    assert refused.json()["code"] == ErrorCode.ACCOUNT_BANNED_UNTIL
    assert refused.json()["params"]["reason"] == "Spam"
    assert datetime.fromisoformat(refused.json()["params"]["ends_at"]) == ends_at
    [entry] = list(db_session.scalars(select(ModerationAction)).all())
    assert (entry.action, entry.target_type, entry.target_id, entry.target_label) == (
        ModerationActionKind.BAN,
        ModerationTargetType.ACCOUNT,
        alice_account.id,
        "alice",
    )


def test_a_session_opened_while_the_ban_was_decided_cannot_be_refreshed(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    assert ban(auth_client, nina, alice_account.id).status_code == 204
    now: datetime = datetime.now(UTC)
    raw_token: str = generate_refresh_token()
    surviving: RefreshToken = RefreshToken(
        user_id=alice_account.id,
        token_hash=hash_refresh_token(raw_token),
        family_id=uuid.uuid4(),
        authenticated_at=now,
        expires_at=now + timedelta(days=1),
    )
    db_session.add(surviving)
    db_session.flush()
    auth_client.cookies.clear()
    auth_client.cookies.set(REFRESH_TOKEN_COOKIE, raw_token)

    response: Response = auth_client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.SESSION_EXPIRED
    db_session.expire_all()
    assert surviving.revoked_at is not None


def test_a_permanent_ban_has_no_end(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    ban(auth_client, nina, account(db_session, "alice@example.com").id)

    refused: Response = login(auth_client, "alice@example.com")

    assert refused.status_code == 403
    assert refused.json()["code"] == ErrorCode.ACCOUNT_BANNED
    assert refused.json()["params"] == {"reason": "Repeated harassment"}


def test_a_wrong_password_does_not_say_that_the_account_is_banned(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    ban(auth_client, nina, account(db_session, "alice@example.com").id)
    auth_client.cookies.clear()

    response: Response = auth_client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong password!"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == ErrorCode.INVALID_CREDENTIALS


def test_a_temporary_ban_ends_by_itself(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ban(auth_client, nina, alice_account.id, datetime.now(UTC) + timedelta(days=1))
    [current] = bans_of(db_session, alice_account)
    current.ends_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()

    assert login(auth_client, "alice@example.com").status_code == 200


def test_banning_a_banned_account_replaces_its_ban(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ban(auth_client, nina, alice_account.id, datetime.now(UTC) + timedelta(days=1))

    response: Response = ban(auth_client, nina, alice_account.id)

    assert response.status_code == 204
    first, second = bans_of(db_session, alice_account)
    assert first.lifted_at is not None
    assert (second.ends_at, second.lifted_at) == (None, None)


def test_two_simultaneous_bans_leave_one_active_ban(migrated_engine: Engine):
    with Session(migrated_engine) as setup:
        banned: User = User(email=f"banned-{uuid.uuid4()}@example.com", display_name="Banned")
        super_admin: User = User(
            email=f"admin-{uuid.uuid4()}@example.com",
            display_name="Admin",
            role=UserRole.SUPER_ADMIN,
        )
        setup.add_all([banned, super_admin])
        setup.commit()
        banned_id: uuid.UUID = banned.id
        super_admin_id: uuid.UUID = super_admin.id

    def ban_too() -> None:
        with Session(migrated_engine) as second_request:
            admin: User = second_request.get_one(User, super_admin_id)
            AccountBanService(
                second_request, ModerationLogService(second_request, get_settings())
            ).ban(admin, banned_id, "Second decision", None)

    try:
        with Session(migrated_engine) as first_request:
            locked: User | None = user_repository.get_user_for_update(first_request, banned_id)
            assert locked is not None
            first_request.add(
                AccountBan(
                    user_id=banned_id,
                    actor_id=super_admin_id,
                    actor_name="Admin",
                    reason="First decision",
                )
            )
            first_request.flush()
            second_request_thread: threading.Thread = threading.Thread(target=ban_too)
            second_request_thread.start()
            time.sleep(0.3)
            first_request.commit()
            second_request_thread.join(timeout=10)

        with Session(migrated_engine) as session:
            active_bans: list[AccountBan] = list(
                session.scalars(
                    select(AccountBan).where(
                        AccountBan.user_id == banned_id, AccountBan.lifted_at.is_(None)
                    )
                ).all()
            )
        assert [ban.reason for ban in active_bans] == ["Second decision"]
    finally:
        with Session(migrated_engine) as cleanup:
            cleanup.execute(delete(ModerationAction).where(ModerationAction.target_id == banned_id))
            cleanup.execute(delete(User).where(User.id.in_([banned_id, super_admin_id])))
            cleanup.commit()


def test_lifting_a_ban_lets_the_account_sign_in_again(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ban(auth_client, nina, alice_account.id)

    response: Response = lift(auth_client, nina, alice_account.id, "Appeal accepted")

    assert response.status_code == 204
    assert login(auth_client, "alice@example.com").status_code == 200
    entries: list[ModerationAction] = list(
        db_session.scalars(select(ModerationAction).order_by(ModerationAction.created_at)).all()
    )
    assert [(entry.action, entry.reason) for entry in entries] == [
        (ModerationActionKind.BAN, "Repeated harassment"),
        (ModerationActionKind.LIFT_BAN, "Appeal accepted"),
    ]


def test_lifting_without_an_active_ban_is_refused(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    response: Response = lift(auth_client, nina, account(db_session, "alice@example.com").id)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.ACCOUNT_NOT_BANNED


@pytest.mark.parametrize("target", ["nina@example.com", "sam@example.com"])
def test_a_super_admin_cannot_be_banned_not_even_by_themselves(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], target: str
):
    register_super_admin(auth_client, db_session, "sam@example.com")

    response: Response = ban(auth_client, nina, account(db_session, target).id)

    assert response.status_code == 409
    assert response.json()["code"] == ErrorCode.CANNOT_BAN_SUPER_ADMIN
    assert db_session.scalars(select(AccountBan)).all() == []


def test_the_end_of_a_ban_must_be_in_the_future(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    response: Response = ban(
        auth_client,
        nina,
        account(db_session, "alice@example.com").id,
        datetime.now(UTC) - timedelta(minutes=1),
    )

    assert response.status_code == 422
    assert response.json()["code"] == ErrorCode.BAN_END_IN_PAST


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_a_ban_needs_a_reason_of_at_most_500_characters(
    auth_client: TestClient,
    db_session: Session,
    nina: dict[str, str],
    alice: dict[str, str],
    reason: str,
):
    response: Response = ban(
        auth_client, nina, account(db_session, "alice@example.com").id, reason=reason
    )

    assert response.status_code == 422


@pytest.mark.parametrize("action", ["ban", "lift-ban"])
def test_an_unknown_account_is_not_found(
    auth_client: TestClient, nina: dict[str, str], action: str
):
    response: Response = auth_client.post(
        f"/moderation/accounts/{UNKNOWN_ID}/{action}", json={"reason": "Spam"}, headers=nina
    )

    assert response.status_code == 404
    assert response.json()["code"] == ErrorCode.ACCOUNT_NOT_FOUND


@pytest.mark.parametrize("action", ["ban", "lift-ban"])
def test_the_ban_routes_require_a_super_admin(
    auth_client: TestClient, alice: dict[str, str], action: str
):
    path: str = f"/moderation/accounts/{UNKNOWN_ID}/{action}"

    without_session: Response = auth_client.post(path, json={"reason": "Spam"})
    other_account: Response = auth_client.post(path, json={"reason": "Spam"}, headers=alice)

    assert without_session.status_code == 401
    assert other_account.status_code == 403
    assert other_account.json()["code"] == ErrorCode.SUPER_ADMIN_REQUIRED


def test_the_account_page_and_the_search_show_the_active_ban(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ends_at: datetime = datetime.now(UTC) + timedelta(days=3)
    ban(auth_client, nina, alice_account.id, ends_at)

    page: JsonObject = auth_client.get(
        f"/moderation/accounts/{alice_account.id}", headers=nina
    ).json()
    found: JsonObject = auth_client.get(
        "/moderation/accounts", params={"query": "alice"}, headers=nina
    ).json()["accounts"][0]

    assert page["ban"]["reason"] == "Repeated harassment"
    assert page["ban"]["actor_name"] == "nina"
    assert datetime.fromisoformat(page["ban"]["ends_at"]) == ends_at
    assert found["banned"] is True


def test_deleting_the_account_deletes_its_bans(
    auth_client: TestClient, db_session: Session, nina: dict[str, str], alice: dict[str, str]
):
    alice_account: User = account(db_session, "alice@example.com")
    ban(auth_client, nina, alice_account.id, datetime.now(UTC) + timedelta(days=1))
    alice_id: uuid.UUID = alice_account.id

    db_session.delete(alice_account)
    db_session.flush()

    assert db_session.scalars(select(AccountBan).where(AccountBan.user_id == alice_id)).all() == []
