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
    accounts: list[User]
    guest_nicknames: list[str]


def seat(session: Session, settings: Settings, room: Room, seats: Seats) -> None:
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


def ban_an_account_and_a_guest(session: Session, room: Room, account: User, nickname: str) -> None:
    room.bans.append(RoomBan(user_id=account.id, display_name=account.display_name))
    room.bans.append(
        RoomBan(guest_token_hash=hash_guest_token(generate_guest_token()), display_name=nickname)
    )
    room.version += 1
    session.commit()


def _guest(settings: Settings, nickname: str) -> Participant:
    return Participant(
        nickname=nickname,
        guest_token_hash=hash_guest_token(generate_guest_token()),
        guest_expires_at=datetime.now(UTC) + timedelta(days=settings.guest_link_ttl_days),
    )
