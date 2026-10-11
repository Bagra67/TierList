from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.participant import Participant
from app.models.room import Room


def add_room(session: Session, room: Room) -> None:
    session.add(room)


def get_room_by_code(session: Session, code: str, for_update: bool = False) -> Room | None:
    """Salle de ce code, avec son template et ses participants (et leur utilisateur).

    for_update verrouille la ligne de la salle jusqu'à la fin de la transaction : deux
    modifications de la même salle passent l'une après l'autre (docs/technical/realtime.md)."""
    statement: Select[Room] = (
        select(Room)
        .where(Room.code == code)
        .options(
            selectinload(Room.template),
            selectinload(Room.participants).selectinload(Participant.user),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return session.scalars(statement).one_or_none()
