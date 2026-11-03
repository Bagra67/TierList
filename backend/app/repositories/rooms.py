import uuid
from datetime import datetime

from sqlalchemy import Exists, Select, select, update
from sqlalchemy.orm import Session, selectinload, with_expression
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.sql.dml import ReturningUpdate

from app.models.enums import RoomStatus
from app.models.game import Game
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.room import Room
from app.models.round import Round
from app.models.template_snapshot import TemplateSnapshot
from app.repositories import games as game_repository


def add_room(session: Session, room: Room) -> None:
    session.add(room)


def _room_with_details(statement: Select[Room], for_update: bool) -> Select[Room]:
    statement = statement.options(
        selectinload(Room.template),
        selectinload(Room.participants).selectinload(Participant.user),
        selectinload(Room.bans),
        selectinload(Room.current_game).selectinload(Game.rounds).selectinload(Round.tile),
        selectinload(Room.current_game)
        .selectinload(Game.snapshot)
        .selectinload(TemplateSnapshot.tiers),
        selectinload(Room.current_game).selectinload(Game.placements).selectinload(Placement.tile),
        selectinload(Room.closed_games).options(
            selectinload(Game.snapshot),
            with_expression(Game.player_count, game_repository.player_count_expression()),
        ),
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return statement


def _attach_room_to_participants(room: Room | None) -> Room | None:
    if room is not None:
        for participant in room.participants:
            set_committed_value(participant, "room", room)
    return room


def get_room_by_code(session: Session, code: str, for_update: bool = False) -> Room | None:
    statement: Select[Room] = _room_with_details(select(Room).where(Room.code == code), for_update)
    return _attach_room_to_participants(session.scalars(statement).one_or_none())


def get_room_by_id(session: Session, room_id: uuid.UUID, for_update: bool = False) -> Room | None:
    statement: Select[Room] = _room_with_details(select(Room).where(Room.id == room_id), for_update)
    return _attach_room_to_participants(session.scalars(statement).one_or_none())


def get_participant(session: Session, participant_id: uuid.UUID) -> Participant | None:
    return session.get(Participant, participant_id)


def get_room_of_participant(
    session: Session, participant_id: uuid.UUID, for_update: bool = False
) -> Room | None:
    statement: Select[Room] = (
        select(Room)
        .join(Participant, Participant.room_id == Room.id)
        .where(Participant.id == participant_id)
        .options(selectinload(Room.participants).selectinload(Participant.user))
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return session.scalars(statement).one_or_none()


def list_room_ids_of_admin(session: Session, admin_id: uuid.UUID) -> list[uuid.UUID]:
    return list(session.scalars(select(Room.id).where(Room.admin_id == admin_id)).all())


def list_inactive_room_ids(session: Session, cutoff: datetime) -> list[uuid.UUID]:
    someone_connected: Exists = (
        select(Participant.id)
        .where(Participant.room_id == Room.id, Participant.connected.is_(True))
        .exists()
    )
    statement: Select[uuid.UUID] = select(Room.id).where(
        Room.status == RoomStatus.OPEN, Room.updated_at < cutoff, ~someone_connected
    )
    return list(session.scalars(statement).all())


def delete_room(session: Session, room: Room) -> None:
    session.delete(room)


def disconnect_everyone(session: Session) -> int:
    statement: ReturningUpdate[uuid.UUID] = (
        update(Participant)
        .where(Participant.connected.is_(True))
        .values(connected=False)
        .returning(Participant.id)
    )
    return len(session.scalars(statement).all())
