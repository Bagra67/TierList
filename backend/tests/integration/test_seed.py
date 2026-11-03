import logging
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.core.config import get_settings
from app.models.account_ban import AccountBan
from app.models.enums import (
    GameStatus,
    PlacementPhase,
    RoomStatus,
    TemplateModeration,
    UserRole,
)
from app.models.game import Game
from app.models.image import Image, ImageStatus
from app.models.moderation_action import ModerationAction
from app.models.placement import Placement
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.models.template import Template
from app.models.user import User
from app.seed.accounts import seed_email
from app.seed.run import SeedSummary, run_seed
from app.seed.sizes import SMALL_SIZE
from app.services.image_storage import quarantine_key
from tests.integration.conftest import FakeImageStorage
from tests.integration.helpers import JsonObject, counted_queries

pytestmark = pytest.mark.integration

SEED_PASSWORD = "seed-test-password"
SMALL_SEED_MAX_QUERIES = 500
MODERATION_ACTIONS = (
    SMALL_SIZE.moderation_actions
    + SMALL_SIZE.hidden_images
    + SMALL_SIZE.deleted_images
    + SMALL_SIZE.hidden_templates
    + SMALL_SIZE.temporarily_banned_accounts
    + SMALL_SIZE.permanently_banned_accounts
)


def seed(db_session: Session, stored_images: dict[str, bytes]) -> SeedSummary:
    return run_seed(
        db_session, get_settings(), FakeImageStorage(stored_images), SMALL_SIZE, SEED_PASSWORD
    )


def count(db_session: Session, model: type) -> int:
    return db_session.scalar(select(func.count()).select_from(model)) or 0


def sign_in(client: TestClient, email: str) -> dict[str, str]:
    response: Response = client.post(
        "/auth/login", json={"email": email, "password": SEED_PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_the_seed_creates_every_kind_of_data(db_session: Session, stored_images: dict[str, bytes]):
    summary: SeedSummary = seed(db_session, stored_images)

    accounts: int = (
        SMALL_SIZE.super_admins
        + SMALL_SIZE.players
        + SMALL_SIZE.unverified_accounts
        + SMALL_SIZE.google_accounts
    )
    assert count(db_session, User) == accounts == summary.accounts
    assert (
        db_session.scalar(
            select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
        )
        == SMALL_SIZE.super_admins
    )
    assert db_session.scalar(
        select(func.count()).select_from(User).where(User.email_verified_at.is_(None))
    ) == (SMALL_SIZE.unverified_accounts)
    assert count(db_session, Template) == summary.templates
    assert (
        db_session.scalar(
            select(func.count()).select_from(Template).where(Template.deleted_at.is_not(None))
        )
        == SMALL_SIZE.deleted_templates
    )
    assert count(db_session, Image) == summary.images
    hidden_keys: list[str] = list(
        db_session.scalars(
            select(Image.storage_key).where(Image.status == ImageStatus.HIDDEN)
        ).all()
    )
    assert len(hidden_keys) == SMALL_SIZE.hidden_images
    assert all(quarantine_key(key) in stored_images for key in hidden_keys)
    assert (
        db_session.scalar(
            select(func.count()).select_from(Image).where(Image.status == ImageStatus.DELETED)
        )
        == SMALL_SIZE.deleted_images
    )
    assert len(stored_images) == summary.images - SMALL_SIZE.deleted_images
    first_upload, last_upload = db_session.execute(
        select(func.min(Image.created_at), func.max(Image.created_at))
    ).one()
    assert last_upload - first_upload > timedelta(days=1)
    assert count(db_session, Game) == SMALL_SIZE.closed_games
    assert (
        db_session.scalar(
            select(func.count()).select_from(Game).where(Game.status != GameStatus.CLOSED)
        )
        == 0
    )
    # Des votes absents, comme dans une vraie partie
    assert db_session.scalar(
        select(func.count())
        .select_from(Placement)
        .where(Placement.phase == PlacementPhase.ROUND, Placement.snapshot_tier_id.is_(None))
    )
    open_rooms: int = SMALL_SIZE.lobby_rooms + SMALL_SIZE.full_rooms + SMALL_SIZE.rooms_with_bans
    assert (
        db_session.scalar(
            select(func.count()).select_from(Room).where(Room.status == RoomStatus.OPEN)
        )
        == open_rooms
        == summary.open_rooms
    )
    assert count(db_session, RoomBan) == 2 * SMALL_SIZE.rooms_with_bans
    assert count(db_session, ModerationAction) == MODERATION_ACTIONS == summary.moderation_actions
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(ModerationAction)
            .where(ModerationAction.target_id.in_(select(Image.id)))
        )
        == SMALL_SIZE.hidden_images + SMALL_SIZE.deleted_images
    )
    hidden_template_ids: list[uuid.UUID] = list(
        db_session.scalars(
            select(Template.id).where(Template.moderation == TemplateModeration.HIDDEN)
        ).all()
    )
    assert len(hidden_template_ids) == SMALL_SIZE.hidden_templates
    assert db_session.scalar(
        select(func.count())
        .select_from(Room)
        .where(Room.status == RoomStatus.OPEN, Room.template_id.in_(hidden_template_ids))
    )


def test_running_the_seed_again_replaces_its_data_only(
    db_session: Session, stored_images: dict[str, bytes]
):
    real_user: User = User(email="real@example.com", display_name="Real")
    db_session.add(real_user)
    db_session.flush()
    db_session.add(Template(owner_id=real_user.id, name="Mine"))
    db_session.commit()
    seed(db_session, stored_images)
    first_keys: set[str] = set(stored_images)

    seed(db_session, stored_images)

    accounts: int = (
        SMALL_SIZE.super_admins
        + SMALL_SIZE.players
        + SMALL_SIZE.unverified_accounts
        + SMALL_SIZE.google_accounts
    )
    assert count(db_session, User) == accounts + 1
    assert count(db_session, Game) == SMALL_SIZE.closed_games
    assert count(db_session, ModerationAction) == MODERATION_ACTIONS
    assert db_session.scalars(
        select(Template.name).where(Template.owner_id == real_user.id)
    ).all() == ["Mine"]
    assert count(db_session, Image) == len(stored_images) + SMALL_SIZE.deleted_images
    assert first_keys.isdisjoint(stored_images)


def test_the_seeded_history_and_results_work_through_the_api(
    client: TestClient, db_session: Session, stored_images: dict[str, bytes]
):
    seed(db_session, stored_images)
    headers: dict[str, str] = sign_in(client, seed_email("player", 1))

    first_page: Response = client.get("/history", headers=headers)
    second_page: Response = client.get("/history?offset=20", headers=headers)

    assert first_page.status_code == 200
    assert len(first_page.json()["games"]) == 20
    assert first_page.json()["has_more"] is True
    assert second_page.json()["games"]
    token: str = first_page.json()["games"][0]["public_token"]
    results: Response = client.get(f"/results/{token}")
    assert results.status_code == 200
    body: JsonObject = results.json()
    assert body["players"]


def test_the_seeded_banned_accounts_cannot_sign_in(
    client: TestClient, db_session: Session, stored_images: dict[str, bytes]
):
    seed(db_session, stored_images)
    banned: list[uuid.UUID] = list(db_session.scalars(select(AccountBan.user_id)).all())
    emails: list[str] = list(
        db_session.scalars(select(User.email).where(User.id.in_(banned))).all()
    )

    responses: list[Response] = [
        client.post("/auth/login", json={"email": email, "password": SEED_PASSWORD})
        for email in emails
    ]

    assert len(emails) == (
        SMALL_SIZE.temporarily_banned_accounts + SMALL_SIZE.permanently_banned_accounts
    )
    assert sorted(response.json()["code"] for response in responses) == [
        ErrorCode.ACCOUNT_BANNED,
        ErrorCode.ACCOUNT_BANNED_UNTIL,
    ]
    assert seed_email("player", 1) not in emails


def test_a_seeded_super_admin_reads_the_moderation_log(
    client: TestClient, db_session: Session, stored_images: dict[str, bytes]
):
    seed(db_session, stored_images)
    headers: dict[str, str] = sign_in(client, seed_email("admin", 1))

    response: Response = client.get("/moderation/log", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["entries"]) == 50
    assert response.json()["has_more"] is True


def test_the_seed_logs_each_step_and_its_progress(
    db_session: Session, stored_images: dict[str, bytes], caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.INFO, logger="app.seed")

    seed(db_session, stored_images)

    messages: list[str] = [record.getMessage() for record in caplog.records]
    for step in range(1, 7):
        assert any(message.startswith(f"Étape {step}/6") for message in messages)
        assert any(
            message.startswith(f"Étape {step}/6") and " terminée en " in message
            for message in messages
        )
    last_game: str = f"Partie terminée {SMALL_SIZE.closed_games}/{SMALL_SIZE.closed_games}"
    assert any(message.startswith(last_game) for message in messages)


def test_the_seed_needs_few_queries(db_session: Session, stored_images: dict[str, bytes]):
    with counted_queries(db_session) as statements:
        seed(db_session, stored_images)

    assert len(statements) <= SMALL_SEED_MAX_QUERIES
