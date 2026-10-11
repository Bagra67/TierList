"""Règles métier des salles : création à partir d'un template, lecture et réglages.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Une salle n'est visible que de ses participants ; seul son room admin change les réglages.
"""

import logging
import secrets
import uuid
from typing import TypedDict

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.rooms import (
    FRONTEND_ROOM,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    ROOM_CODE_MAX_ATTEMPTS,
)
from app.core.config import Settings
from app.exceptions.rooms import RoomAdminRequiredError, RoomNotFoundError, RoomSettingsLockedError
from app.exceptions.templates import TemplateHasNoTilesError, TemplateNotFoundError
from app.models.participant import Participant
from app.models.room import AutoAdvance, ItemOrder, Room, RoomStatus
from app.models.template import Template
from app.models.user import User
from app.repositories import rooms as room_repository
from app.repositories import templates as template_repository

logger = logging.getLogger(__name__)

# Contrainte d'unicité du code (convention de nommage de app/db/base.py)
ROOM_CODE_CONSTRAINT = "uq_rooms_code"


def generate_room_code() -> str:
    """Code aléatoire de ROOM_CODE_LENGTH caractères de ROOM_CODE_ALPHABET (secrets : il ne se
    devine pas à partir des codes déjà vus)."""
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


class RoomSettingsChanges(TypedDict, total=False):
    """Modifications des réglages : seules les clés présentes changent. Chaque clé est une
    colonne de Room, recopiée telle quelle."""

    item_order: ItemOrder
    auto_advance: AutoAdvance
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


# Seul réglage modifiable pendant une partie (US-2.10, #88)
SETTINGS_CHANGEABLE_DURING_A_GAME: frozenset[str] = frozenset({"late_arrivals_allowed"})


class RoomService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def create(self, owner: User, template_id: uuid.UUID) -> Room:
        """Crée une salle ouverte à partir d'un template du propriétaire qui a au moins une
        tuile ; le propriétaire en devient le room admin, avec sa place, et les réglages par
        défaut s'appliquent."""
        template: Template | None = template_repository.get_owned_template(
            self._session, template_id, owner.id
        )
        if template is None:
            raise TemplateNotFoundError
        if not template.tiles:
            raise TemplateHasNoTilesError

        for _ in range(ROOM_CODE_MAX_ATTEMPTS):
            room: Room = Room(
                code=generate_room_code(),
                admin_id=owner.id,
                template_id=template.id,
                timer_seconds=self._settings.room_default_timer_seconds,
                cooldown_seconds=self._settings.room_default_cooldown_seconds,
                participants=[Participant(user_id=owner.id)],
            )
            if self._insert_unless_code_taken(room):
                self._session.commit()
                logger.info(
                    "Salle créée : room_id=%s code=%s admin_id=%s template_id=%s",
                    room.id,
                    room.code,
                    owner.id,
                    template.id,
                )
                return room

        # Ne devrait jamais arriver : ce serait le signe de codes presque tous pris
        logger.error("Aucun code de salle libre après %d tirages", ROOM_CODE_MAX_ATTEMPTS)
        raise RuntimeError("No free room code")

    def get(self, user: User, code: str) -> Room:
        """Salle dont l'utilisateur est participant ; le code est lu sans tenir compte de la
        casse (un code tapé en minuscules est le même)."""
        return self._get_as_participant(user, code, for_update=False)

    def update_settings(self, user: User, code: str, changes: RoomSettingsChanges) -> Room:
        """Change les réglages de la prochaine partie (room admin seulement). Pendant une partie,
        seules les arrivées peuvent changer."""
        room: Room = self._get_as_participant(user, code, for_update=True)
        if room.admin_id != user.id:
            raise RoomAdminRequiredError
        if room.status == RoomStatus.PLAYING and not (
            changes.keys() <= SETTINGS_CHANGEABLE_DURING_A_GAME
        ):
            raise RoomSettingsLockedError
        for field_name, value in changes.items():
            setattr(room, field_name, value)
        # Sans modification, le commit libère seulement le verrou
        self._session.commit()
        return room

    def link(self, room: Room) -> str:
        """Lien de la salle à partager, vers sa page du frontend."""
        return f"{self._settings.frontend_base_url}{FRONTEND_ROOM}/{room.code}"

    def _get_as_participant(self, user: User, code: str, for_update: bool) -> Room:
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=for_update
        )
        if room is None:
            raise RoomNotFoundError
        if not any(participant.user_id == user.id for participant in room.participants):
            raise RoomNotFoundError
        return room

    def _insert_unless_code_taken(self, room: Room) -> bool:
        """Insère la salle dans un savepoint ; False si son code est déjà pris (la transaction
        reste utilisable pour un autre tirage). Toute autre erreur d'intégrité remonte."""
        try:
            with self._session.begin_nested():
                room_repository.add_room(self._session, room)
        except IntegrityError as exc:
            if (
                isinstance(exc.orig, UniqueViolation)
                and exc.orig.diag.constraint_name == ROOM_CODE_CONSTRAINT
            ):
                logger.info("Code de salle déjà pris, nouveau tirage : code=%s", room.code)
                return False
            raise
        return True
