"""Places et bannissements des salles du jeu de données, écrits directement.

RoomService.join recharge toute la salle (places, comptes, bannissements, parties) à chaque
arrivée : près de vingt requêtes par place, des minutes sur staging, à travers Internet. Les
salles sont donc créées par le service (code, place du room admin, réglages), puis leurs places
écrites ici, en une fois, avec les mêmes règles : un compte au plus une fois par salle, un pseudo
d'invité unique sans tenir compte de la casse, au plus FREE_PLAN_MAX_PARTICIPANTS places, le jeton
d'un invité gardé seulement par son empreinte, et un bannissement qui remplace la place."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.constants.rooms import FREE_PLAN_MAX_PARTICIPANTS
from app.core.config import Settings
from app.core.security import generate_guest_token, hash_guest_token
from app.models.participant import Participant
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.models.user import User

GUEST_NICKNAMES: tuple[str, ...] = (
    "Lou", "Max", "Tom", "Eva", "Noé", "Mia", "Léo", "Jade", "Ana", "Kim", "Ugo", "Liv",
)  # fmt: skip


@dataclass(frozen=True)
class Seats:
    """Qui prend place dans une salle, en plus de son room admin."""

    accounts: list[User]
    guest_nicknames: list[str]


def seat(session: Session, settings: Settings, room: Room, seats: Seats) -> None:
    """Donne leur place aux comptes et aux invités, puis valide la transaction."""
    taken: set[str] = {participant.display_name.lower() for participant in room.participants}
    seated: list[Participant] = [Participant(user_id=account.id) for account in seats.accounts]
    taken |= {account.display_name.lower() for account in seats.accounts}
    for nickname in seats.guest_nicknames:
        if nickname.lower() in taken:
            continue
        taken.add(nickname.lower())
        seated.append(_guest(settings, nickname))
    assert len(room.participants) + len(seated) <= FREE_PLAN_MAX_PARTICIPANTS
    room.participants.extend(seated)
    room.version += 1
    session.commit()


def ban(session: Session, room: Room, account: User, nickname: str) -> None:
    """Un compte et un invité bannis, comme après RoomService.remove_participant(ban=True) : le
    bannissement garde le compte ou l'empreinte du jeton, et le nom affiché ; la place n'existe
    plus."""
    room.bans.append(RoomBan(user_id=account.id, display_name=account.display_name))
    room.bans.append(
        RoomBan(guest_token_hash=hash_guest_token(generate_guest_token()), display_name=nickname)
    )
    room.version += 1
    session.commit()


def _guest(settings: Settings, nickname: str) -> Participant:
    """Une place d'invité, comme RoomService.join_as_guest : seule l'empreinte du jeton est
    gardée (personne n'utilisera ce lien perso)."""
    return Participant(
        nickname=nickname,
        guest_token_hash=hash_guest_token(generate_guest_token()),
        guest_expires_at=datetime.now(UTC) + timedelta(days=settings.guest_link_ttl_days),
    )
