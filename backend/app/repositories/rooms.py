import uuid
from datetime import datetime

from sqlalchemy import Exists, Select, select, update
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.sql.dml import ReturningUpdate

from app.models.enums import RoomStatus
from app.models.game import Game
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.room import Room
from app.models.round import Round
from app.models.template_snapshot import TemplateSnapshot


def add_room(session: Session, room: Room) -> None:
    session.add(room)


def _room_with_details(statement: Select[Room], for_update: bool) -> Select[Room]:
    """Charge avec la salle son template, ses participants (et leur utilisateur), ses
    bannissements, sa partie en cours (ses tours et leur tuile, ses tiers, ses placements) et
    ses parties closes (leurs joueurs).

    for_update verrouille la ligne de la salle jusqu'à la fin de la transaction : deux
    modifications de la même salle passent l'une après l'autre (docs/technical/realtime.md)."""
    statement = statement.options(
        selectinload(Room.template),
        selectinload(Room.participants).selectinload(Participant.user),
        selectinload(Room.bans),
        selectinload(Room.current_game).selectinload(Game.rounds).selectinload(Round.tile),
        selectinload(Room.current_game)
        .selectinload(Game.snapshot)
        .selectinload(TemplateSnapshot.tiers),
        selectinload(Room.current_game).selectinload(Game.placements).selectinload(Placement.tile),
        selectinload(Room.closed_games).selectinload(Game.players),
    )
    if for_update:
        statement = statement.with_for_update(of=Room)
    return statement


def _attach_room_to_participants(room: Room | None) -> Room | None:
    """Renseigne participant.room sur chaque place chargée. L'identity map ne garde que des
    références faibles : un appelant qui ne garde que la place (seat_of) perdrait la salle
    chargée, et participant.room la relirait, avec sa partie, une requête par tuile."""
    if room is not None:
        for participant in room.participants:
            set_committed_value(participant, "room", room)
    return room


def get_room_by_code(session: Session, code: str, for_update: bool = False) -> Room | None:
    """Salle de ce code, avec tout ce que sa réponse montre (_room_with_details)."""
    statement: Select[Room] = _room_with_details(select(Room).where(Room.code == code), for_update)
    return _attach_room_to_participants(session.scalars(statement).one_or_none())


def get_room_by_id(session: Session, room_id: uuid.UUID, for_update: bool = False) -> Room | None:
    """Salle de cet identifiant, chargée comme get_room_by_code : pour une transition décidée
    par le serveur (timer, déconnexion), qui ne connaît pas le code."""
    statement: Select[Room] = _room_with_details(select(Room).where(Room.id == room_id), for_update)
    return _attach_room_to_participants(session.scalars(statement).one_or_none())


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


def list_room_ids_of_admin(session: Session, admin_id: uuid.UUID) -> list[uuid.UUID]:
    """Identifiants des salles dont ce compte est le room admin."""
    return list(session.scalars(select(Room.id).where(Room.admin_id == admin_id)).all())


def list_inactive_room_ids(session: Session, cutoff: datetime) -> list[uuid.UUID]:
    """Identifiants des salles inactives (US-2.8) : ouvertes, sans changement depuis cutoff
    (rooms.updated_at suit chaque version), et où personne n'est connecté."""
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
    """Supprime la salle avec ses places et ses bannissements ; la base détache ses parties
    (games.room_id SET NULL), qui lui survivent (invariant 11)."""
    session.delete(room)


def disconnect_everyone(session: Session) -> int:
    """Remet tous les participants à déconnecté ; renvoie leur nombre."""
    statement: ReturningUpdate[uuid.UUID] = (
        update(Participant)
        .where(Participant.connected.is_(True))
        .values(connected=False)
        .returning(Participant.id)
    )
    return len(session.scalars(statement).all())
