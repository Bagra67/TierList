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
    RoomNotJoinedError,
    RoomSettingsLockedError,
)
from app.exceptions.templates import (
    TemplateHasNoTilesError,
    TemplateHiddenError,
    TemplateNotFoundError,
)
from app.models.enums import (
    AutoAdvance,
    ItemOrder,
    PlacementPhase,
    RoomStatus,
    TemplateModeration,
)
from app.models.game import Game
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.models.template import Template
from app.models.user import User
from app.repositories import games as game_repository
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
from app.services.room_channel import PostCommitRoomPublisher

logger = logging.getLogger(__name__)


def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


class RoomSettingsChanges(TypedDict, total=False):
    item_order: ItemOrder
    auto_advance: AutoAdvance
    timer_seconds: int
    cooldown_seconds: int
    admin_plays: bool
    late_arrivals_allowed: bool


SETTINGS_CHANGEABLE_DURING_A_GAME: frozenset[str] = frozenset({"late_arrivals_allowed"})


@dataclass(frozen=True)
class RoomViewer:
    user: User | None
    guest_token: str | None


@dataclass(frozen=True)
class GuestSeat:
    room: Room
    participant: Participant
    token: str

    @property
    def expires_at(self) -> datetime:
        expires_at: datetime | None = self.participant.guest_expires_at
        if expires_at is None:
            raise RuntimeError("A guest seat has an expiry date")
        return expires_at


class RoomService:
    def __init__(
        self, session: Session, settings: Settings, publisher: PostCommitRoomPublisher
    ) -> None:
        self._session = session
        self._settings = settings
        self._publisher = publisher

    def create(self, owner: User, template_id: uuid.UUID) -> Room:
        template: Template | None = template_repository.get_owned_template(
            self._session, template_id, owner.id
        )
        if template is None:
            raise TemplateNotFoundError
        if template.moderation == TemplateModeration.HIDDEN:
            raise TemplateHiddenError
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
                    "Salle créée : room_id=%s admin_id=%s template_id=%s",
                    room.id,
                    owner.id,
                    template.id,
                )
                return room

        logger.error("Aucun code de salle libre après %d tirages", ROOM_CODE_MAX_ATTEMPTS)
        raise RuntimeError("No free room code")

    def get_for_admin_change(self, user: User, code: str) -> Room:
        room: Room = self._get_as_participant(user, code, for_update=True)
        if room.admin_id != user.id:
            raise RoomAdminRequiredError
        return room

    def join(self, user: User, code: str) -> Room:
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        if any(room_ban.user_id == user.id for room_ban in room.bans):
            raise RoomBannedError
        if self._has_seat(room, user):
            self._release_room_lock()
            return room
        self._ensure_can_arrive(room)
        player: Participant = Participant(user_id=user.id)
        room.participants.append(player)
        self._absent_for_past_rounds(room, player)
        room.version += 1
        self._session.commit()
        logger.info("Salle rejointe : room_id=%s user_id=%s", room.id, user.id)
        self._publish_joined(room, player)
        return room

    def join_as_guest(self, code: str, nickname: str, guest_token: str | None) -> GuestSeat:
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=True
        )
        if room is None:
            raise RoomNotFoundError
        if guest_token is not None and self._is_banned_guest(room, guest_token):
            raise RoomBannedError
        now: datetime = datetime.now(UTC)
        for participant in list(room.participants):
            if participant.has_expired(now):
                room.participants.remove(participant)
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
            self._absent_for_past_rounds(room, guest)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if violates_unique(exc, NICKNAME_INDEX):
                raise NicknameTakenError from exc
            raise
        logger.info("Salle rejointe en invité : room_id=%s participant_id=%s", room.id, guest.id)
        self._publish_joined(room, guest)
        return GuestSeat(room=room, participant=guest, token=token)

    def restore_guest(self, code: str, token: str) -> GuestSeat:
        room: Room | None = room_repository.get_room_by_code(self._session, code.upper())
        if room is None:
            raise GuestLinkInvalidError
        guest: Participant | None = self._find_guest(room, token)
        if guest is None:
            raise GuestLinkInvalidError
        return GuestSeat(room=room, participant=guest, token=token)

    def renew_guest_link(self, viewer: RoomViewer, code: str) -> GuestSeat:
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

    def closed_games(self, room: Room) -> list[Game]:
        return game_repository.list_closed_games_of_room(self._session, room.id)

    def seated_participants(self, room: Room) -> list[Participant]:
        now: datetime = datetime.now(UTC)
        return [
            participant for participant in room.participants if not participant.has_expired(now)
        ]

    def guest_link(self, seat: GuestSeat) -> str:
        return f"{self.link(seat.room)}#{GUEST_LINK_FRAGMENT}={seat.token}"

    def update_settings(self, user: User, code: str, changes: RoomSettingsChanges) -> Room:
        room: Room = self.get_for_admin_change(user, code)
        if room.status == RoomStatus.PLAYING and not (
            changes.keys() <= SETTINGS_CHANGEABLE_DURING_A_GAME
        ):
            raise RoomSettingsLockedError
        for field_name, value in changes.items():
            setattr(room, field_name, value)
        if changes:
            room.version += 1
        self._session.commit()
        if changes:
            self._publisher.publish(room.id, RoomSettingsUpdatedEvent(room_version=room.version))
        return room

    def _release_room_lock(self) -> None:
        self._session.commit()

    def remove_participant(
        self, user: User, code: str, participant_id: uuid.UUID, ban: bool
    ) -> Room:
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
        close_code: int = CHANNEL_CLOSE_BANNED if ban else CHANNEL_CLOSE_REMOVED
        reason: ErrorCode = ErrorCode.ROOM_BANNED if ban else ErrorCode.REMOVED_FROM_ROOM
        self._remove_seat(room, target, close_code, reason)
        return room

    def remove_seat_of_deleted_account(self, participant_id: uuid.UUID) -> Room | None:
        room: Room | None = room_repository.get_room_of_participant(
            self._session, participant_id, for_update=True
        )
        target: Participant | None = None
        if room is not None:
            target = next((p for p in room.participants if p.id == participant_id), None)
        if room is None or target is None:
            self._release_room_lock()
            return None
        self._remove_seat(room, target, CHANNEL_CLOSE_REMOVED, ErrorCode.REMOVED_FROM_ROOM)
        return room

    def _remove_seat(
        self, room: Room, target: Participant, close_code: int, reason: ErrorCode
    ) -> None:
        participant_id: uuid.UUID = target.id
        room.participants.remove(target)
        room.version += 1
        self._session.commit()
        logger.info(
            "Participant retiré : room_id=%s participant_id=%s close_code=%s",
            room.id,
            participant_id,
            close_code,
        )
        self._publisher.disconnect_participant(room.id, participant_id, close_code, reason)
        self._publisher.publish(
            room.id,
            ParticipantRemovedEvent(
                room_version=room.version,
                data=ParticipantRemovedData(participant_id=participant_id),
            ),
        )

    def unban(self, user: User, code: str, ban_id: uuid.UUID) -> Room:
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

    def seat_of(self, viewer: RoomViewer, code: str, for_update: bool = False) -> Participant:
        room: Room | None = room_repository.get_room_by_code(
            self._session, code.upper(), for_update=for_update
        )
        if room is None:
            raise RoomNotFoundError
        if viewer.user is not None:
            return self.seat_in(room, viewer.user)
        if viewer.guest_token is not None:
            guest: Participant | None = self._find_guest(room, viewer.guest_token)
            if guest is not None:
                return guest
        raise RoomNotJoinedError

    @staticmethod
    def seat_in(room: Room, user: User) -> Participant:
        for participant in room.participants:
            if participant.user_id == user.id:
                return participant
        raise RoomNotJoinedError

    def set_presence(self, participant_id: uuid.UUID, connected: bool) -> Room | None:
        room: Room | None = room_repository.get_room_of_participant(
            self._session, participant_id, for_update=True
        )
        participant: Participant | None = None
        if room is not None:
            participant = next((p for p in room.participants if p.id == participant_id), None)
        if room is None or participant is None or participant.connected == connected:
            self._release_room_lock()
            return None
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
        return room

    def reset_presence(self) -> int:
        reset_count: int = room_repository.disconnect_everyone(self._session)
        self._session.commit()
        return reset_count

    def link(self, room: Room) -> str:
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

    def _absent_for_past_rounds(self, room: Room, participant: Participant) -> None:
        game: Game | None = room.current_game
        if game is None:
            return
        self._session.flush()
        for game_round in game.rounds:
            if game_round.ended_at is not None:
                absent: Placement = Placement(
                    participant_id=participant.id,
                    snapshot_tile_id=game_round.snapshot_tile_id,
                    phase=PlacementPhase.ROUND,
                )
                game.placements.append(absent)

    def _ensure_can_arrive(self, room: Room) -> None:
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
        return {participant.display_name.lower() for participant in room.participants}

    @staticmethod
    def _is_banned_guest(room: Room, token: str) -> bool:
        token_hash: str = hash_guest_token(token)
        return any(room_ban.guest_token_hash == token_hash for room_ban in room.bans)

    @staticmethod
    def _find_guest(room: Room, token: str) -> Participant | None:
        token_hash: str = hash_guest_token(token)
        now: datetime = datetime.now(UTC)
        for participant in room.participants:
            if participant.guest_token_hash == token_hash and not participant.has_expired(now):
                return participant
        return None

    def _insert_unless_code_taken(self, room: Room) -> bool:
        try:
            with self._session.begin_nested():
                room_repository.add_room(self._session, room)
        except IntegrityError as exc:
            if violates_unique(exc, ROOM_CODE_CONSTRAINT):
                logger.info("Code de salle déjà pris, nouveau tirage")
                return False
            raise
        return True
