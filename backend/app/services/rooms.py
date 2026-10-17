"""Règles métier des salles : création à partir d'un template, jonction (compte ou invité),
lecture, réglages, retrait et bannissement des participants.

Le service possède les frontières de transaction : chaque opération se termine par un commit.
Chaque changement de la salle incrémente sa version et est publié aux sockets de la salle après le
commit (docs/technical/realtime.md). Une salle n'est visible que de ses participants ; seul son
room admin change les réglages, retire ou bannit un participant.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.error_codes import ErrorCode
from app.constants.rooms import (
    CHANNEL_CLOSE_BANNED,
    CHANNEL_CLOSE_REMOVED,
    FREE_PLAN_MAX_PARTICIPANTS,
    FRONTEND_ROOM,
    GUEST_LINK_FRAGMENT,
    NICKNAME_INDEX,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_CONSTRAINT,
    ROOM_CODE_LENGTH,
    ROOM_CODE_MAX_ATTEMPTS,
)
from app.core.config import Settings
from app.core.security import generate_guest_token, hash_guest_token
from app.db.errors import violates_unique
from app.exceptions.rooms import (
    BanNotFoundError,
    CannotRemoveRoomAdminError,
    GuestLinkInvalidError,
    NicknameTakenError,
    ParticipantNotFoundError,
    RoomAdminRequiredError,
    RoomBannedError,
    RoomFullError,
    RoomLockedError,
    RoomNotFoundError,
    RoomSettingsLockedError,
)
from app.exceptions.templates import TemplateHasNoTilesError, TemplateNotFoundError
from app.models.enums import AutoAdvance, ItemOrder, RoomStatus
from app.models.participant import Participant
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.models.template import Template
from app.models.user import User
from app.repositories import rooms as room_repository
from app.repositories import templates as template_repository
from app.schemas.room_events import (
    ParticipantJoinedData,
    ParticipantJoinedEvent,
    ParticipantPresenceData,
    ParticipantPresenceEvent,
    ParticipantRemovedData,
    ParticipantRemovedEvent,
    RoomSettingsUpdatedEvent,
)
from app.services.room_channel import RoomEventPublisher

logger = logging.getLogger(__name__)


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


# Seul réglage modifiable pendant une partie (US-2.10)
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
    def __init__(self, session: Session, settings: Settings, publisher: RoomEventPublisher) -> None:
        self._session = session
        self._settings = settings
        self._publisher = publisher

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

    def get_for_admin_change(self, user: User, code: str) -> Room:
        """Salle dont l'utilisateur est le room admin, verrouillée jusqu'au commit : pour tout
        changement réservé au room admin, ici ou dans un autre service (démarrer une partie).
        Participant sans être room admin : RoomAdminRequiredError."""
        room: Room = self._get_as_participant(user, code, for_update=True)
        if room.admin_id != user.id:
            raise RoomAdminRequiredError
        return room

    def join(self, user: User, code: str) -> Room:
        """Donne une place de joueur à l'utilisateur (US-2.4) ; s'il en a déjà une, il la
        retrouve au lieu d'en prendre une seconde, même si la salle est pleine ou verrouillée.
        Le code suffit : qui l'a peut rejoindre, sauf un compte banni de la salle (US-2.12), ou un
        nouveau venu quand la salle est pleine (US-2.6) ou verrouillée (US-2.10)."""
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        if any(room_ban.user_id == user.id for room_ban in room.bans):
            raise RoomBannedError
        if self._has_seat(room, user):
            # Rien à écrire : le commit libère seulement le verrou
            self._session.commit()
            return room
        self._ensure_can_arrive(room)
        # Le verrou de la salle sérialise deux jonctions simultanées du même utilisateur ; la
        # contrainte (room_id, user_id) reste le dernier filet
        player: Participant = Participant(user_id=user.id)
        room.participants.append(player)
        room.version += 1
        self._session.commit()
        logger.info("Salle rejointe : room_id=%s user_id=%s", room.id, user.id)
        self._publish_joined(room, player)
        return room

    def join_as_guest(self, code: str, nickname: str, guest_token: str | None) -> GuestSeat:
        """Donne une place d'invité (US-2.5) : un pseudo suffit, unique dans la salle sans tenir
        compte de la casse. L'invité reçoit un jeton valable guest_link_ttl_days, porté par son
        cookie et son lien perso ; il n'est jamais lié à un compte.

        guest_token est le jeton du cookie que ce navigateur a déjà pour la salle : s'il est celui
        d'un invité banni, la jonction est refusée. C'est au mieux (US-2.12) : un navigateur sans
        ce cookie n'est pas reconnu."""
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        if guest_token is not None and self._is_banned_guest(room, guest_token):
            raise RoomBannedError
        now: datetime = datetime.now(UTC)
        # Les invités dont le lien a expiré ont perdu leur place : elle libère leur pseudo
        for participant in list(room.participants):
            if participant.has_expired(now):
                room.participants.remove(participant)
        # Supprimées tout de suite : au flush, SQLAlchemy passe les INSERT avant les DELETE, et
        # le nouvel invité buterait sur l'index unique du pseudo libéré
        self._session.flush()
        self._ensure_can_arrive(room)
        if nickname.lower() in self._taken_names(room):
            raise NicknameTakenError
        token: str = generate_guest_token()
        guest: Participant = Participant(
            nickname=nickname,
            guest_token_hash=hash_guest_token(token),
            guest_expires_at=now + timedelta(days=self._settings.guest_link_ttl_days),
        )
        room.participants.append(guest)
        room.version += 1
        try:
            self._session.commit()
        except IntegrityError as exc:
            # Dernier filet : lower() de PostgreSQL et str.lower() de Python peuvent différer sur
            # quelques caractères Unicode ; l'index refuse alors un pseudo que le service a laissé
            # passer. C'est le même refus, pas une erreur interne.
            self._session.rollback()
            if violates_unique(exc, NICKNAME_INDEX):
                raise NicknameTakenError from exc
            raise
        logger.info("Salle rejointe en invité : room_id=%s participant_id=%s", room.id, guest.id)
        self._publish_joined(room, guest)
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

    def renew_guest_link(self, viewer: RoomViewer, code: str) -> GuestSeat:
        """Nouveau lien perso pour l'invité reconnu par son cookie, qui a perdu le sien : un
        nouveau jeton remplace l'ancien, qui cesse de marcher (lien comme cookie). La date
        d'expiration ne change pas : le renouvellement ne prolonge pas la place."""
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None or viewer.user is not None or viewer.guest_token is None:
            raise RoomNotFoundError
        guest: Participant | None = self._find_guest(room, viewer.guest_token)
        if guest is None:
            raise RoomNotFoundError
        token: str = generate_guest_token()
        guest.guest_token_hash = hash_guest_token(token)
        self._session.commit()
        logger.info("Lien perso renouvelé : room_id=%s participant_id=%s", room.id, guest.id)
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
        room: Room = self.get_for_admin_change(user, code)
        if room.status == RoomStatus.PLAYING and not (
            changes.keys() <= SETTINGS_CHANGEABLE_DURING_A_GAME
        ):
            raise RoomSettingsLockedError
        for field_name, value in changes.items():
            setattr(room, field_name, value)
        if changes:
            room.version += 1
        # Sans modification, le commit libère seulement le verrou
        self._session.commit()
        if changes:
            self._publisher.publish(room.id, RoomSettingsUpdatedEvent(room_version=room.version))
        return room

    def remove_participant(
        self, user: User, code: str, participant_id: uuid.UUID, ban: bool
    ) -> Room:
        """Supprime la place d'un participant (room admin seulement, US-2.11), même pendant une
        partie. Avec ban, la personne est aussi bannie (US-2.12) : son compte, ou pour un invité
        l'empreinte du jeton de son cookie. Ses sockets sont fermés après le commit."""
        room: Room = self.get_for_admin_change(user, code)
        target: Participant | None = next(
            (
                participant
                for participant in self.seated_participants(room)
                if participant.id == participant_id
            ),
            None,
        )
        if target is None:
            raise ParticipantNotFoundError
        if target.user_id == room.admin_id:
            raise CannotRemoveRoomAdminError
        if ban:
            room_ban: RoomBan = RoomBan(
                user_id=target.user_id,
                guest_token_hash=target.guest_token_hash,
                display_name=target.display_name,
            )
            room.bans.append(room_ban)
        room.participants.remove(target)
        room.version += 1
        self._session.commit()
        logger.info(
            "Participant retiré : room_id=%s participant_id=%s banned=%s",
            room.id,
            participant_id,
            ban,
        )
        # Ses sockets d'abord : il quitte la salle avant la diffusion, et ne reçoit pas l'événement
        close_code: int = CHANNEL_CLOSE_BANNED if ban else CHANNEL_CLOSE_REMOVED
        reason: ErrorCode = ErrorCode.ROOM_BANNED if ban else ErrorCode.REMOVED_FROM_ROOM
        self._publisher.disconnect_participant(room.id, participant_id, close_code, reason)
        self._publisher.publish(
            room.id,
            ParticipantRemovedEvent(
                room_version=room.version,
                data=ParticipantRemovedData(participant_id=participant_id),
            ),
        )
        return room

    def unban(self, user: User, code: str, ban_id: uuid.UUID) -> Room:
        """Lève un bannissement (room admin seulement) : la personne peut rejoindre à nouveau.
        Seul le room admin voit les bannissements : la version de la salle ne change pas."""
        room: Room = self.get_for_admin_change(user, code)
        room_ban: RoomBan | None = next(
            (room_ban for room_ban in room.bans if room_ban.id == ban_id), None
        )
        if room_ban is None:
            raise BanNotFoundError
        room.bans.remove(room_ban)
        self._session.commit()
        logger.info("Bannissement levé : room_id=%s ban_id=%s", room.id, ban_id)
        return room

    def seat_of(self, viewer: RoomViewer, code: str) -> Participant:
        """Place du lecteur dans la salle (compte ou invité) : elle lui ouvre le canal temps réel.
        Sans place, RoomNotFoundError, comme pour la lecture de la salle."""
        room: Room = self.get_for_viewer(viewer, code)
        for participant in self.seated_participants(room):
            if viewer.user is not None and participant.user_id == viewer.user.id:
                return participant
        if viewer.user is None and viewer.guest_token is not None:
            guest: Participant | None = self._find_guest(room, viewer.guest_token)
            if guest is not None:
                return guest
        raise RoomNotFoundError

    def set_presence(self, participant_id: uuid.UUID, connected: bool) -> None:
        """Marque le participant connecté ou déconnecté. N'écrit et ne publie que si la présence
        change ; une place disparue entre-temps (salle fermée) est ignorée."""
        room: Room | None = room_repository.get_room_of_participant(
            self._session, participant_id, for_update=True
        )
        participant: Participant | None = None
        if room is not None:
            participant = next((p for p in room.participants if p.id == participant_id), None)
        if room is None or participant is None or participant.connected == connected:
            # Rien à écrire : le commit libère seulement le verrou
            self._session.commit()
            return
        participant.connected = connected
        room.version += 1
        self._session.commit()
        self._publisher.publish(
            room.id,
            ParticipantPresenceEvent(
                room_version=room.version,
                data=ParticipantPresenceData(participant_id=participant_id, connected=connected),
            ),
        )

    def reset_presence(self) -> int:
        """Au démarrage du processus, plus aucun socket n'est ouvert : personne n'est connecté.
        Renvoie le nombre de participants remis à déconnecté."""
        reset_count: int = room_repository.disconnect_everyone(self._session)
        self._session.commit()
        return reset_count

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

    def _ensure_can_arrive(self, room: Room) -> None:
        """Un nouveau venu peut-il prendre une place ? Pas pendant une partie aux arrivées
        verrouillées, ni dans une salle pleine. Appelé sous le verrou de la salle : deux jonctions
        simultanées ne dépassent pas la limite."""
        if room.status == RoomStatus.PLAYING and not room.late_arrivals_allowed:
            raise RoomLockedError
        if len(self.seated_participants(room)) >= FREE_PLAN_MAX_PARTICIPANTS:
            raise RoomFullError(FREE_PLAN_MAX_PARTICIPANTS)

    def _publish_joined(self, room: Room, participant: Participant) -> None:
        self._publisher.publish(
            room.id,
            ParticipantJoinedEvent(
                room_version=room.version,
                data=ParticipantJoinedData(participant_id=participant.id),
            ),
        )

    @staticmethod
    def _has_seat(room: Room, user: User) -> bool:
        return any(participant.user_id == user.id for participant in room.participants)

    @staticmethod
    def _taken_names(room: Room) -> set[str]:
        """Noms affichés de la salle, en minuscules : ceux des comptes et les pseudos des
        invités. Un nouvel invité ne peut prendre aucun d'eux."""
        return {participant.display_name.lower() for participant in room.participants}

    @staticmethod
    def _is_banned_guest(room: Room, token: str) -> bool:
        token_hash: str = hash_guest_token(token)
        return any(room_ban.guest_token_hash == token_hash for room_ban in room.bans)

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
            if violates_unique(exc, ROOM_CODE_CONSTRAINT):
                logger.info("Code de salle déjà pris, nouveau tirage : code=%s", room.code)
                return False
            raise
        return True
