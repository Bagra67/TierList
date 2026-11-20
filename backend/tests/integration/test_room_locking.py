import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.rooms import FREE_PLAN_MAX_PARTICIPANTS
from app.core.config import get_settings
from app.core.security import hash_guest_token
from app.exceptions.rooms import RoomFullError
from app.models.participant import Participant
from app.models.room import Room
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.repositories import rooms as room_repository
from app.services.rooms import RoomService
from app.services.templates import TemplateService
from tests.integration.conftest import RecordingRoomEventPublisher

pytestmark = pytest.mark.integration

SECOND_REQUEST_HEAD_START_SECONDS = 0.3


@dataclass(frozen=True)
class CommittedRoom:
    code: str
    room_id: uuid.UUID
    admin_id: uuid.UUID
    bob_id: uuid.UUID


@pytest.fixture
def committed_room(migrated_engine: Engine) -> Iterator[CommittedRoom]:
    with Session(migrated_engine) as session:
        admin: User = User(email=f"admin-{uuid.uuid4()}@example.com", display_name="Admin")
        bob: User = User(email=f"bob-{uuid.uuid4()}@example.com", display_name="Bob")
        session.add_all([admin, bob])
        session.flush()
        template: Template = TemplateService(session, get_settings()).create(admin, "Locked")
        template.tiles.append(Tile(text="Tile", position=0))
        session.commit()
        room: Room = room_service(session).create(admin, template.id)
        committed: CommittedRoom = CommittedRoom(room.code, room.id, admin.id, bob.id)
    try:
        yield committed
    finally:
        with Session(migrated_engine) as session:
            session.execute(delete(Room).where(Room.id == committed.room_id))
            session.execute(delete(User).where(User.id.in_([committed.admin_id, committed.bob_id])))
            session.commit()


def room_service(session: Session) -> RoomService:
    return RoomService(session, get_settings(), RecordingRoomEventPublisher())


def guest_seat(nickname: str) -> Participant:
    return Participant(
        nickname=nickname,
        guest_token_hash=hash_guest_token(nickname),
        guest_expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def locked_room(session: Session, code: str) -> Room:
    room: Room | None = room_repository.get_room_by_code(session, code, for_update=True)
    assert room is not None
    return room


def seat_count(migrated_engine: Engine, room_id: uuid.UUID) -> int:
    with Session(migrated_engine) as session:
        count: int | None = session.scalar(
            select(func.count()).select_from(Participant).where(Participant.room_id == room_id)
        )
    return count or 0


def test_two_simultaneous_joins_stay_within_the_limit(
    migrated_engine: Engine, committed_room: CommittedRoom
):
    errors: list[Exception] = []

    with Session(migrated_engine) as first_request:
        room: Room = locked_room(first_request, committed_room.code)
        for index in range(FREE_PLAN_MAX_PARTICIPANTS - 1):
            room.participants.append(guest_seat(f"Guest{index}"))
        first_request.flush()

        def join_one_too_many() -> None:
            with Session(migrated_engine) as second_request:
                bob: User | None = second_request.get(User, committed_room.bob_id)
                assert bob is not None
                try:
                    room_service(second_request).join(bob, committed_room.code)
                except RoomFullError as error:
                    errors.append(error)

        second_request_thread: threading.Thread = threading.Thread(target=join_one_too_many)
        second_request_thread.start()
        time.sleep(SECOND_REQUEST_HEAD_START_SECONDS)
        first_request.commit()
        second_request_thread.join(timeout=10)

    assert len(errors) == 1
    assert seat_count(migrated_engine, committed_room.room_id) == FREE_PLAN_MAX_PARTICIPANTS


def test_two_simultaneous_joins_of_one_account_give_one_seat(
    migrated_engine: Engine, committed_room: CommittedRoom
):
    errors: list[Exception] = []

    with Session(migrated_engine) as first_request:
        room: Room = locked_room(first_request, committed_room.code)
        room.participants.append(Participant(user_id=committed_room.bob_id))
        first_request.flush()

        def join_again() -> None:
            with Session(migrated_engine) as second_request:
                bob: User | None = second_request.get(User, committed_room.bob_id)
                assert bob is not None
                try:
                    room_service(second_request).join(bob, committed_room.code)
                except IntegrityError as error:
                    errors.append(error)

        second_request_thread: threading.Thread = threading.Thread(target=join_again)
        second_request_thread.start()
        time.sleep(SECOND_REQUEST_HEAD_START_SECONDS)
        first_request.commit()
        second_request_thread.join(timeout=10)

    assert errors == []
    assert seat_count(migrated_engine, committed_room.room_id) == 2


def test_the_database_keeps_one_seat_per_account(
    migrated_engine: Engine, committed_room: CommittedRoom
):
    with Session(migrated_engine) as session:
        session.add(Participant(room_id=committed_room.room_id, user_id=committed_room.admin_id))

        with pytest.raises(IntegrityError):
            session.flush()


def test_an_empty_settings_change_releases_the_lock_of_the_room(
    migrated_engine: Engine, committed_room: CommittedRoom
):
    with Session(migrated_engine) as request:
        admin: User | None = request.get(User, committed_room.admin_id)
        assert admin is not None

        room_service(request).update_settings(admin, committed_room.code, {})

        with Session(migrated_engine) as next_request:
            locked_without_waiting: Room | None = next_request.scalar(
                select(Room).where(Room.id == committed_room.room_id).with_for_update(nowait=True)
            )
            assert locked_without_waiting is not None
