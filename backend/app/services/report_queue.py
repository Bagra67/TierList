import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.exceptions.reports import (
    GameModerationConflictError,
    GameNotFoundError,
    NicknameNotFoundError,
    ReportsNotOpenError,
)
from app.models.enums import (
    GameStatus,
    ModerationActionKind,
    ModerationTargetType,
    ReportReason,
    ReportStatus,
)
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.participant import Participant
from app.models.report import Report
from app.models.user import User
from app.repositories import games as game_repository
from app.repositories import images as image_repository
from app.repositories import reports as report_repository
from app.repositories import rooms as room_repository
from app.repositories import users as user_repository
from app.repositories.reports import OpenReportGroup
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)

REMOVED_NICKNAME_PREFIX = "#"
REMOVED_NICKNAME_RANDOM_LENGTH = 8


@dataclass(frozen=True)
class ReportedContent:
    target_type: ModerationTargetType
    target_id: uuid.UUID
    label: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    report_count: int
    reasons: list[tuple[ReportReason, int]]
    details: list[str]
    first_reported_at: datetime
    image: Image | None
    public_token: str | None


@dataclass(frozen=True)
class HiddenGamesPage:
    games: list[Game]
    has_more: bool


@dataclass(frozen=True)
class ReportQueuePage:
    contents: list[ReportedContent]
    has_more: bool


class ReportQueueService:
    def __init__(
        self, session: Session, settings: Settings, moderation_log: ModerationLogService
    ) -> None:
        self._session = session
        self._settings = settings
        self._moderation_log = moderation_log

    def page(self, limit: int, offset: int, owner_id: uuid.UUID | None) -> ReportQueuePage:
        groups: list[OpenReportGroup] = report_repository.list_open_report_groups(
            self._session, limit + 1, offset, owner_id
        )
        shown_groups: list[OpenReportGroup] = groups[:limit]
        target_ids: list[uuid.UUID] = [group.target_id for group in shown_groups]
        reports_per_target: dict[tuple[ModerationTargetType, uuid.UUID], list[Report]] = {}
        for report in report_repository.list_open_reports_of_targets(self._session, target_ids):
            reports_per_target.setdefault((report.target_type, report.target_id), []).append(report)
        images: dict[uuid.UUID, Image] = image_repository.images_by_id(
            self._session, _targets_of_type(shown_groups, ModerationTargetType.IMAGE)
        )
        public_tokens: dict[uuid.UUID, str | None] = game_repository.public_tokens_by_game(
            self._session, _targets_of_type(shown_groups, ModerationTargetType.GAME)
        )
        owner_ids: list[uuid.UUID] = [
            report.owner_id
            for reports in reports_per_target.values()
            for report in reports
            if report.owner_id is not None
        ]
        owner_names: dict[uuid.UUID, str] = user_repository.display_names_by_id(
            self._session, owner_ids
        )
        contents: list[ReportedContent] = []
        for group in shown_groups:
            reports: list[Report] = reports_per_target[(group.target_type, group.target_id)]
            owner: uuid.UUID | None = reports[0].owner_id
            reasons: Counter[ReportReason] = Counter(report.reason for report in reports)
            contents.append(
                ReportedContent(
                    target_type=group.target_type,
                    target_id=group.target_id,
                    label=reports[0].target_label,
                    owner_id=owner,
                    owner_name=owner_names.get(owner) if owner is not None else None,
                    report_count=group.report_count,
                    reasons=reasons.most_common(),
                    details=[report.details for report in reports if report.details is not None],
                    first_reported_at=group.first_reported_at,
                    image=images.get(group.target_id),
                    public_token=public_tokens.get(group.target_id),
                )
            )
        return ReportQueuePage(contents=contents, has_more=len(groups) > limit)

    def count_open_contents(self) -> int:
        return report_repository.count_open_report_groups(self._session)

    def dismiss(
        self,
        super_admin: User,
        target_type: ModerationTargetType,
        target_id: uuid.UUID,
        reason: str,
    ) -> None:
        reports: list[Report] = report_repository.list_open_reports_of_target_for_update(
            self._session, target_type, target_id
        )
        if not reports:
            raise ReportsNotOpenError
        action: ModerationAction = self._moderation_log.record(
            super_admin,
            ModerationActionKind.DISMISS,
            target_type,
            target_id,
            reports[0].target_label or str(target_id),
            reason,
        )
        report_repository.close_open_reports(
            self._session, target_type, [target_id], ReportStatus.DISMISSED, action.id
        )
        self._session.commit()
        logger.info(
            "Signalements classés : target_type=%s target_id=%s super_admin_id=%s reports=%d",
            target_type,
            target_id,
            super_admin.id,
            len(reports),
        )

    def remove_nickname(self, super_admin: User, target_id: uuid.UUID, reason: str) -> None:
        user: User | None = user_repository.get_user_by_id(self._session, target_id)
        replacement: str = _removed_nickname()
        nickname: str
        closed_targets: list[uuid.UUID]
        if user is not None:
            nickname = user.display_name
            closed_targets = [user.id]
            user.display_name = replacement
            game_repository.rename_players_of_account(self._session, user.id, replacement)
        else:
            nickname, closed_targets = self._rename_guest(target_id, replacement)
        action: ModerationAction = self._moderation_log.record(
            super_admin,
            ModerationActionKind.DELETE,
            ModerationTargetType.NICKNAME,
            target_id,
            nickname,
            reason,
        )
        report_repository.close_open_reports(
            self._session,
            ModerationTargetType.NICKNAME,
            closed_targets,
            ReportStatus.ACTIONED,
            action.id,
        )
        self._session.commit()
        logger.info("Pseudo retiré : target_id=%s super_admin_id=%s", target_id, super_admin.id)

    def hide_game(self, super_admin: User, game_id: uuid.UUID, reason: str) -> None:
        game: Game = self._get_closed_game(game_id)
        if game.hidden_at is not None:
            raise GameModerationConflictError
        game.hidden_at = datetime.now(UTC)
        action: ModerationAction = self._moderation_log.record(
            super_admin,
            ModerationActionKind.HIDE,
            ModerationTargetType.GAME,
            game.id,
            game.snapshot.name,
            reason,
        )
        report_repository.close_open_reports(
            self._session,
            ModerationTargetType.GAME,
            [game.id],
            ReportStatus.ACTIONED,
            action.id,
        )
        self._session.commit()
        logger.info("Partie masquée : game_id=%s super_admin_id=%s", game_id, super_admin.id)

    def unhide_game(self, super_admin: User, game_id: uuid.UUID, reason: str) -> None:
        game: Game = self._get_closed_game(game_id)
        if game.hidden_at is None:
            raise GameModerationConflictError
        game.hidden_at = None
        self._moderation_log.record(
            super_admin,
            ModerationActionKind.UNHIDE,
            ModerationTargetType.GAME,
            game.id,
            game.snapshot.name,
            reason,
        )
        self._session.commit()
        logger.info("Partie réaffichée : game_id=%s super_admin_id=%s", game_id, super_admin.id)

    def hidden_games(self, limit: int, offset: int) -> HiddenGamesPage:
        games: list[Game] = game_repository.list_hidden_games(self._session, limit + 1, offset)
        return HiddenGamesPage(games=games[:limit], has_more=len(games) > limit)

    def purge_closed(self) -> int:
        limit: datetime = datetime.now(UTC) - timedelta(
            days=self._settings.closed_report_retention_days
        )
        purged: int = report_repository.delete_reports_closed_before(self._session, limit)
        self._session.commit()
        logger.info("Signalements fermés purgés : %d (avant %s)", purged, limit.isoformat())
        return purged

    def _rename_guest(self, target_id: uuid.UUID, replacement: str) -> tuple[str, list[uuid.UUID]]:
        participant: Participant | None = room_repository.get_participant(self._session, target_id)
        player: GamePlayer | None = (
            game_repository.get_game_player(self._session, target_id)
            if participant is None
            else None
        )
        room_id: uuid.UUID | None
        nickname: str | None
        if participant is not None:
            room_id, nickname = participant.room_id, participant.nickname
        elif player is not None and player.user_id is None:
            room_id, nickname = player.game.room_id, player.display_name
        else:
            raise NicknameNotFoundError
        if nickname is None:
            raise NicknameNotFoundError
        guest: Participant | None = (
            participant
            if participant is not None
            else (
                room_repository.get_guest_of_room(self._session, room_id, nickname)
                if room_id is not None
                else None
            )
        )
        players: list[GamePlayer] = (
            game_repository.list_guest_players_of_room(self._session, room_id, nickname)
            if room_id is not None
            else [player]
            if player is not None
            else []
        )
        closed_targets: list[uuid.UUID] = [other.id for other in players]
        if guest is not None:
            guest.nickname = replacement
            closed_targets.append(guest.id)
        for other in players:
            other.display_name = replacement
        return nickname, closed_targets

    def _get_closed_game(self, game_id: uuid.UUID) -> Game:
        game: Game | None = game_repository.get_game_for_update(self._session, game_id)
        if game is None or game.status is not GameStatus.CLOSED:
            raise GameNotFoundError
        return game


def _removed_nickname() -> str:
    return f"{REMOVED_NICKNAME_PREFIX}{uuid.uuid4().hex[:REMOVED_NICKNAME_RANDOM_LENGTH]}"


def _targets_of_type(
    groups: list[OpenReportGroup], target_type: ModerationTargetType
) -> list[uuid.UUID]:
    return [group.target_id for group in groups if group.target_type == target_type]
