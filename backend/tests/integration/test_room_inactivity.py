"""Fermeture automatique des salles inactives (US-2.8) : une salle ouverte où personne n'est
connecté, sans changement depuis le délai d'inactivité, est fermée comme par son room admin."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import build_game_service
from app.core.config import get_settings
from app.models.participant import Participant
from app.models.room import Room
from app.repositories import rooms as room_repository
from app.services.games import GameService
from tests.integration.conftest import RecordingRoomEventPublisher, RecordingRoundScheduler
from tests.integration.helpers import JsonObject, create_room, create_template, register, start_game

pytestmark = pytest.mark.integration

INACTIVE_FOR: timedelta = timedelta(hours=24)


@pytest.fixture
def alice(auth_client: TestClient) -> dict[str, str]:
    return register(auth_client, "alice@example.com")


@pytest.fixture
def alice_room(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
) -> JsonObject:
    template_id: str = create_template(auth_client, db_session, alice, tile_count=2)
    return create_room(auth_client, alice, template_id)


def games(
    db_session: Session, publisher: RecordingRoomEventPublisher, scheduler: RecordingRoundScheduler
) -> GameService:
    """Le service hors requête, comme le lance le balayage."""
    return build_game_service(db_session, get_settings(), publisher, scheduler)


def last_changed(db_session: Session, code: str, hours_ago: float) -> uuid.UUID:
    """La salle n'a plus changé depuis hours_ago heures ; renvoie son identifiant."""
    changed_at: datetime = datetime.now(UTC) - timedelta(hours=hours_ago)
    db_session.execute(update(Room).where(Room.code == code).values(updated_at=changed_at))
    db_session.expire_all()
    return db_session.scalars(select(Room.id).where(Room.code == code)).one()


def room_codes(db_session: Session) -> list[str]:
    return list(db_session.scalars(select(Room.code)).all())


def test_an_empty_room_without_change_for_the_delay_is_closed(
    db_session: Session,
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    room_id: uuid.UUID = last_changed(db_session, alice_room["code"], hours_ago=25)

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 1
    assert room_codes(db_session) == []
    assert room_events.closed_rooms == [room_id]


def test_a_room_changed_within_the_delay_stays_open(
    db_session: Session,
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    last_changed(db_session, alice_room["code"], hours_ago=23)

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 0
    assert room_codes(db_session) == [alice_room["code"]]


def test_a_room_with_someone_connected_stays_open(
    db_session: Session,
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    # Alice reste dans le lobby sans rien changer : le heartbeat n'écrit rien en base
    db_session.execute(update(Participant).values(connected=True))
    last_changed(db_session, alice_room["code"], hours_ago=25)

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 0
    assert room_codes(db_session) == [alice_room["code"]]


def test_a_room_in_game_is_never_closed_for_inactivity(
    auth_client: TestClient,
    db_session: Session,
    alice: dict[str, str],
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    start_game(auth_client, alice_room["code"], alice)
    last_changed(db_session, alice_room["code"], hours_ago=25)

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 0
    assert room_codes(db_session) == [alice_room["code"]]


def test_a_room_active_again_is_checked_under_its_lock(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    # La liste a été lue avant qu'Alice ne revienne : la salle est revérifiée sous son verrou
    room_id: uuid.UUID = last_changed(db_session, alice_room["code"], hours_ago=1)
    monkeypatch.setattr(
        room_repository, "list_inactive_room_ids", lambda session, cutoff: [room_id]
    )

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 0
    assert room_codes(db_session) == [alice_room["code"]]
    assert room_events.closed_rooms == []


def test_a_change_of_the_room_restarts_the_delay(
    auth_client: TestClient,
    db_session: Session,
    alice_room: JsonObject,
    room_events: RecordingRoomEventPublisher,
    round_scheduler: RecordingRoundScheduler,
):
    last_changed(db_session, alice_room["code"], hours_ago=25)
    # Bob rejoint la salle : la version change, rooms.updated_at avec elle
    bob: dict[str, str] = register(auth_client, "bob@example.com")
    assert auth_client.post(f"/rooms/{alice_room['code']}/join", headers=bob).status_code == 200

    closed_count: int = games(db_session, room_events, round_scheduler).close_inactive_rooms(
        INACTIVE_FOR
    )

    assert closed_count == 0
    assert room_codes(db_session) == [alice_room["code"]]
