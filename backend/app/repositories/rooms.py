import uuid

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.dml import ReturningUpdate

from app.models.participant import Participant
from app.models.room import Room


def add_room(session: Session, room: Room) -> None:
    session.add(room)


def get_room_by_code(session: Session, code: str, for_update: bool = False) -> Room | None:
    """Salle de ce code, avec son template, ses participants (et leur utilisateur) et ses
    bannissements.

    for_update verrouille la ligne de la salle jusqu'à la fin de la transaction : deux
    modifications de la même salle passent l'une après l'autre (docs/technical/realtime.md)."""
    statement: Select[Room] = (
        select(Room)
        .where(Room.code == code)
        .options(
            selectinload(Room.template),
            selectinload(Room.participants).selectinload(Participant.user),
            selectinload(Room.bans),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return session.scalars(statement).one_or_none()


def get_room_of_participant(
    session: Session, participant_id: uuid.UUID, for_update: bool = False
) -> Room | None:
    """Salle de ce participant, avec ses participants ; verrouillée avec for_update."""
    statement: Select[Room] = (
        select(Room)
        .join(Participant, Participant.room_id == Room.id)
        .where(Participant.id == participant_id)
        .options(selectinload(Room.participants).selectinload(Participant.user))
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return session.scalars(statement).one_or_none()


def disconnect_everyone(session: Session) -> int:
    """Remet tous les participants à déconnecté ; renvoie leur nombre."""
    statement: ReturningUpdate[uuid.UUID] = (
        update(Participant)
        .where(Participant.connected.is_(True))
        .values(connected=False)
        .returning(Participant.id)
    )
    return len(session.scalars(statement).all())
