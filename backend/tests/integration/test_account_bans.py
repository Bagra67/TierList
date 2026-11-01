"""Bannissement des comptes (US-1.8) : un compte banni est déconnecté partout et ne peut plus se
connecter jusqu'à la fin du bannissement ; un super admin ne peut jamais être banni."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.models.account_ban import AccountBan
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.moderation_action import ModerationAction
from app.models.user import User
from tests.integration.helpers import PASSWORD, JsonObject, register, register_super_admin

pytestmark = pytest.mark.integration

# Fixe : un identifiant aléatoire dans un parametrize change le nom du test à chaque collecte
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
    # Ses jetons d'accès déjà émis sont refusés, et ses sessions ne se rafraîchissent plus
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

    # De temporaire à définitif
    response: Response = ban(auth_client, nina, alice_account.id)

    assert response.status_code == 204
    first, second = bans_of(db_session, alice_account)
    assert first.lifted_at is not None
    assert (second.ends_at, second.lifted_at) == (None, None)


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
