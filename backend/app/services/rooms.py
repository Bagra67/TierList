"""Règles métier des salles : création à partir d'un template, jonction (compte ou invité),
lecture et réglages.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Une salle n'est visible que de ses participants ; seul son room admin change les réglages.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.rooms import (
    FRONTEND_ROOM,
    GUEST_LINK_FRAGMENT,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    ROOM_CODE_MAX_ATTEMPTS,
)
from app.core.config import Settings
from app.core.security import generate_guest_token, hash_guest_token
from app.exceptions.rooms import (
    GuestLinkInvalidError,
    NicknameTakenError,
    RoomAdminRequiredError,
    RoomNotFoundError,
    RoomSettingsLockedError,
)
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
# Index unique du pseudo des invités dans une salle (app/models/participant.py)
NICKNAME_INDEX = "uq_participants_room_id_lower_nickname"


def _violates(exc: IntegrityError, constraint_name: str) -> bool:
    """L'erreur d'intégrité vient-elle de cette contrainte d'unicité ?"""
    return (
        isinstance(exc.orig, UniqueViolation) and exc.orig.diag.constraint_name == constraint_name
    )


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


@dataclass(frozen=True)
class RoomViewer:
    """Qui lit la salle : un compte (access token), sinon peut-être un invité (jeton de son
    cookie). Un compte connecté passe toujours avant un éventuel cookie d'invité."""

    user: User | None
    guest_token: str | None


@dataclass(frozen=True)
class GuestSeat:
    """Place d'un invité, avec son jeton en clair : il n'existe qu'ici, le temps de poser le
    cookie et de donner le lien perso (la base n'en garde que l'empreinte)."""

    room: Room
    participant: Participant
    token: str


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

    def join(self, user: User, code: str) -> Room:
        """Donne une place de joueur à l'utilisateur (US-2.4) ; s'il en a déjà une, il la
        retrouve au lieu d'en prendre une seconde. Le code suffit : qui l'a peut rejoindre."""
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        if self._has_seat(room, user):
            # Rien à écrire : le commit libère seulement le verrou
            self._session.commit()
            return room
        # Le verrou de la salle sérialise deux jonctions simultanées du même utilisateur ; la
        # contrainte (room_id, user_id) reste le dernier filet
        room.participants.append(Participant(user_id=user.id))
        self._session.commit()
        logger.info("Salle rejointe : room_id=%s user_id=%s", room.id, user.id)
        return room

    def join_as_guest(self, code: str, nickname: str) -> GuestSeat:
        """Donne une place d'invité (US-2.5) : un pseudo suffit, unique dans la salle sans tenir
        compte de la casse. L'invité reçoit un jeton valable guest_link_ttl_days, porté par son
        cookie et son lien perso ; il n'est jamais lié à un compte."""
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        now: datetime = datetime.now(UTC)
        # Les invités dont le lien a expiré ont perdu leur place : elle libère leur pseudo
        for participant in list(room.participants):
            if participant.has_expired(now):
                room.participants.remove(participant)
        # Supprimées tout de suite : au flush, SQLAlchemy passe les INSERT avant les DELETE, et
        # le nouvel invité buterait sur l'index unique du pseudo libéré
        self._session.flush()
        if nickname.lower() in self._taken_names(room):
            raise NicknameTakenError
        token: str = generate_guest_token()
        guest: Participant = Participant(
            nickname=nickname,
            guest_token_hash=hash_guest_token(token),
            guest_expires_at=now + timedelta(days=self._settings.guest_link_ttl_days),
        )
        room.participants.append(guest)
        try:
            self._session.commit()
        except IntegrityError as exc:
            # Dernier filet : lower() de PostgreSQL et str.lower() de Python peuvent différer sur
            # quelques caractères Unicode ; l'index refuse alors un pseudo que le service a laissé
            # passer. C'est le même refus, pas une erreur interne.
            self._session.rollback()
            if _violates(exc, NICKNAME_INDEX):
                raise NicknameTakenError from exc
            raise
        logger.info("Salle rejointe en invité : room_id=%s participant_id=%s", room.id, guest.id)
        return GuestSeat(room=room, participant=guest, token=token)

    def restore_guest(self, code: str, token: str) -> GuestSeat:
        """Retrouve la place d'un invité à partir de son lien perso, depuis n'importe quel
        appareil (US-5.4) ; la validité n'est pas prolongée."""
        room: Room | None = room_repository.get_room_by_code(self._session, code.upper())
        if room is None:
            raise GuestLinkInvalidError
        guest: Participant | None = self._find_guest(room, token)
        if guest is None:
            raise GuestLinkInvalidError
        return GuestSeat(room=room, participant=guest, token=token)

    def get_for_viewer(self, viewer: RoomViewer, code: str) -> Room:
        """Salle dont le lecteur a une place : un compte participant, ou un invité dont le
        cookie porte un jeton valable pour cette salle."""
        if viewer.user is not None:
            return self.get(viewer.user, code)
        room: Room | None = room_repository.get_room_by_code(self._session, code.upper())
        if room is None or viewer.guest_token is None:
            raise RoomNotFoundError
        if self._find_guest(room, viewer.guest_token) is None:
            raise RoomNotFoundError
        return room

    def seated_participants(self, room: Room) -> list[Participant]:
        """Participants qui ont encore leur place : sans les invités dont le lien a expiré."""
        now: datetime = datetime.now(UTC)
        return [
            participant for participant in room.participants if not participant.has_expired(now)
        ]

    def guest_link(self, seat: GuestSeat) -> str:
        """Lien perso de l'invité : le jeton est dans le fragment, que le navigateur n'envoie
        jamais au serveur (ni dans ses journaux)."""
        return f"{self.link(seat.room)}#{GUEST_LINK_FRAGMENT}={seat.token}"

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
        if not self._has_seat(room, user):
            raise RoomNotFoundError
        return room

    @staticmethod
    def _has_seat(room: Room, user: User) -> bool:
        return any(participant.user_id == user.id for participant in room.participants)

    @staticmethod
    def _taken_names(room: Room) -> set[str]:
        """Noms affichés de la salle, en minuscules : ceux des comptes et les pseudos des
        invités. Un nouvel invité ne peut prendre aucun d'eux."""
        return {participant.display_name.lower() for participant in room.participants}

    @staticmethod
    def _find_guest(room: Room, token: str) -> Participant | None:
        """Place d'invité de cette salle dont le jeton est celui-ci, si elle n'a pas expiré."""
        token_hash: str = hash_guest_token(token)
        now: datetime = datetime.now(UTC)
        for participant in room.participants:
            if participant.guest_token_hash == token_hash and not participant.has_expired(now):
                return participant
        return None

    def _insert_unless_code_taken(self, room: Room) -> bool:
        """Insère la salle dans un savepoint ; False si son code est déjà pris (la transaction
        reste utilisable pour un autre tirage). Toute autre erreur d'intégrité remonte."""
        try:
            with self._session.begin_nested():
                room_repository.add_room(self._session, room)
        except IntegrityError as exc:
            if _violates(exc, ROOM_CODE_CONSTRAINT):
                logger.info("Code de salle déjà pris, nouveau tirage : code=%s", room.code)
                return False
            raise
        return True
