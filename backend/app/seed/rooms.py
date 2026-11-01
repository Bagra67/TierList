"""Salles ouvertes du jeu de données (en plus de celles où des parties ont été jouées) : des salles
pleines, et des salles avec un compte et un invité bannis, aux réglages variés.

Une salle ouverte où personne n'est connecté depuis ROOM_INACTIVITY_HOURS est fermée par le
balayage : elles disparaissent donc au bout d'un jour, il suffit de relancer le jeu de données."""

import random
from dataclasses import dataclass

from app.constants.rooms import FREE_PLAN_MAX_PARTICIPANTS
from app.models.participant import Participant
from app.models.room import Room
from app.models.template import Template
from app.models.user import User
from app.seed.games import GUEST_NICKNAMES
from app.seed.sizes import SeedSize
from app.services.rooms import RoomService

# Invités d'une salle pleine : les autres places vont à des comptes
GUESTS_IN_A_FULL_ROOM = 4


@dataclass(frozen=True)
class SeedRooms:
    full: list[Room]
    with_bans: list[Room]


def create_open_rooms(
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
        others: list[User] = [player for player in players if player.id != admin.id]
        if index < size.full_rooms:
            account_seats: int = FREE_PLAN_MAX_PARTICIPANTS - 1 - GUESTS_IN_A_FULL_ROOM
            for account in rng.sample(others, account_seats):
                rooms.join(account, room.code)
            for nickname in rng.sample(GUEST_NICKNAMES, GUESTS_IN_A_FULL_ROOM):
                room = rooms.join_as_guest(room.code, nickname, None).room
            full.append(room)
        else:
            with_bans.append(_room_with_bans(rooms, room, admin, others, rng))
    return SeedRooms(full=full, with_bans=with_bans)


def _room_with_bans(
    rooms: RoomService, room: Room, admin: User, others: list[User], rng: random.Random
) -> Room:
    """Trois comptes et deux invités rejoignent ; le room admin bannit un compte et un invité
    (US-2.12)."""
    accounts: list[User] = rng.sample(others, 3)
    for account in accounts:
        room = rooms.join(account, room.code)
    banned_guest: Participant = rooms.join_as_guest(room.code, "Trublion", None).participant
    room = rooms.join_as_guest(room.code, rng.choice(GUEST_NICKNAMES), None).room
    banned_account: Participant = next(
        participant for participant in room.participants if participant.user_id == accounts[0].id
    )
    room = rooms.remove_participant(admin, room.code, banned_account.id, ban=True)
    return rooms.remove_participant(admin, room.code, banned_guest.id, ban=True)
