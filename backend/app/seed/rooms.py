import logging
import random
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants.rooms import FREE_PLAN_MAX_PARTICIPANTS
from app.core.config import Settings
from app.models.room import Room
from app.models.template import Template
from app.models.user import User
from app.seed.seats import GUEST_NICKNAMES, Seats, ban, seat
from app.seed.sizes import SeedSize
from app.services.rooms import RoomService

logger = logging.getLogger(__name__)

GUESTS_IN_A_FULL_ROOM = 4
# Une salle à bannissements : trois comptes et un invité assis, un compte et un invité bannis
SEATED_ACCOUNTS_BEFORE_BANS = 3
BANNED_GUEST_NICKNAME = "Trublion"


@dataclass(frozen=True)
class SeedRooms:
    full: list[Room]
    with_bans: list[Room]


def create_open_rooms(
    session: Session,
    settings: Settings,
    rooms: RoomService,
    size: SeedSize,
    players: list[User],
    templates: list[Template],
    rng: random.Random,
) -> SeedRooms:
    full: list[Room] = []
    with_bans: list[Room] = []
    for index in range(size.full_rooms + size.rooms_with_bans):
        template: Template = templates[(index * 3 + 1) % len(templates)]
        admin: User = next(player for player in players if player.id == template.owner_id)
        room: Room = rooms.create(admin, template.id)
        room = rooms.update_settings(
            admin,
            room.code,
            {
                "timer_seconds": rng.choice((10, 30, 60, 120)),
                "cooldown_seconds": rng.choice((30, 60, 180)),
                "late_arrivals_allowed": rng.random() < 0.7,
                "admin_plays": rng.random() < 0.8,
            },
        )
        code: str = room.code
        others: list[User] = [player for player in players if player.id != admin.id]
        if index < size.full_rooms:
            account_seats: int = FREE_PLAN_MAX_PARTICIPANTS - 1 - GUESTS_IN_A_FULL_ROOM
            seat(
                session,
                settings,
                room,
                Seats(
                    accounts=rng.sample(others, account_seats),
                    guest_nicknames=rng.sample(GUEST_NICKNAMES, GUESTS_IN_A_FULL_ROOM),
                ),
            )
            full.append(room)
            logger.info("Salle pleine %s : %d places", code, FREE_PLAN_MAX_PARTICIPANTS)
        else:
            picked: list[User] = rng.sample(others, SEATED_ACCOUNTS_BEFORE_BANS + 1)
            # Le premier compte tiré est banni ; les autres et un invité gardent leur place
            seat(
                session,
                settings,
                room,
                Seats(accounts=picked[1:], guest_nicknames=[rng.choice(GUEST_NICKNAMES)]),
            )
            ban(session, room, picked[0], BANNED_GUEST_NICKNAME)
            with_bans.append(room)
            # Le room admin, les comptes et l'invité restés
            places: int = 1 + SEATED_ACCOUNTS_BEFORE_BANS + 1
            logger.info("Salle avec bannis %s : %d places, 2 bannis", code, places)
    return SeedRooms(full=full, with_bans=with_bans)
