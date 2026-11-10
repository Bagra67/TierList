import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.reports import REPORT_OPEN_BY_ACCOUNT_INDEX, REPORT_OPEN_BY_BROWSER_INDEX
from app.core.config import Settings
from app.core.security import hash_guest_token
from app.db.errors import violates_unique
from app.exceptions.reports import (
    ReportAlreadyOpenError,
    ReportDetailsRequiredError,
    ReportLimitReachedError,
    ReportTargetNotFoundError,
)
from app.models.enums import GameStatus, ModerationTargetType, ReportReason, ReportTargetKind
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import ImageStatus
from app.models.participant import Participant
from app.models.report import Report
from app.models.snapshot_tile import SnapshotTile
from app.repositories import games as game_repository
from app.repositories import reports as report_repository
from app.repositories import rooms as room_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountReporter:
    user_id: uuid.UUID


@dataclass(frozen=True)
class BrowserReporter:
    browser_hash: str


Reporter = AccountReporter | BrowserReporter


def reporter_of(user_id: uuid.UUID | None, browser_token: str) -> Reporter:
    if user_id is not None:
        return AccountReporter(user_id)
    return BrowserReporter(hash_guest_token(browser_token))


@dataclass(frozen=True)
class ReportRequest:
    target_kind: ReportTargetKind
    target_id: uuid.UUID
    reason: ReportReason
    details: str | None


@dataclass(frozen=True)
class ReportedContent:
    target_type: ModerationTargetType
    target_id: uuid.UUID
    label: str | None
    owner_id: uuid.UUID | None


class ReportService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def report(self, reporter: Reporter, request: ReportRequest) -> Report:
        details: str | None = request.details or None
        if request.reason is ReportReason.OTHER and details is None:
            raise ReportDetailsRequiredError
        self._check_report_limit(reporter)
        content: ReportedContent = self._reported_content(request.target_kind, request.target_id)
        report: Report = Report(
            reporter_id=reporter.user_id if isinstance(reporter, AccountReporter) else None,
            reporter_browser_hash=(
                reporter.browser_hash if isinstance(reporter, BrowserReporter) else None
            ),
            target_type=content.target_type,
            target_id=content.target_id,
            target_label=content.label,
            owner_id=content.owner_id,
            reason=request.reason,
            details=details,
        )
        report_repository.add_report(self._session, report)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if violates_unique(exc, REPORT_OPEN_BY_ACCOUNT_INDEX) or violates_unique(
                exc, REPORT_OPEN_BY_BROWSER_INDEX
            ):
                raise ReportAlreadyOpenError from exc
            raise
        logger.info(
            "Contenu signalé : report_id=%s target_type=%s target_id=%s",
            report.id,
            report.target_type,
            report.target_id,
        )
        return report

    def _check_report_limit(self, reporter: Reporter) -> None:
        max_reports: int = self._settings.reports_per_hour_max
        since: datetime = datetime.now(UTC) - timedelta(hours=1)
        recent_reports: int = (
            report_repository.count_reports_of_account_since(self._session, reporter.user_id, since)
            if isinstance(reporter, AccountReporter)
            else report_repository.count_reports_of_browser_since(
                self._session, reporter.browser_hash, since
            )
        )
        if recent_reports >= max_reports:
            raise ReportLimitReachedError(max_reports)

    def _reported_content(
        self, target_kind: ReportTargetKind, target_id: uuid.UUID
    ) -> ReportedContent:
        match target_kind:
            case ReportTargetKind.ITEM:
                return self._image_of_item(target_id)
            case ReportTargetKind.PARTICIPANT:
                return self._nickname_of_participant(target_id)
            case ReportTargetKind.PLAYER:
                return self._nickname_of_player(target_id)
            case ReportTargetKind.GAME:
                return self._closed_game(target_id)

    def _image_of_item(self, item_id: uuid.UUID) -> ReportedContent:
        tile: SnapshotTile | None = game_repository.get_snapshot_tile(self._session, item_id)
        if tile is None or tile.image is None or tile.image.status is not ImageStatus.VISIBLE:
            raise ReportTargetNotFoundError
        return ReportedContent(ModerationTargetType.IMAGE, tile.image.id, None, tile.image.owner_id)

    def _nickname_of_participant(self, participant_id: uuid.UUID) -> ReportedContent:
        participant: Participant | None = room_repository.get_participant(
            self._session, participant_id
        )
        if participant is None:
            raise ReportTargetNotFoundError
        return ReportedContent(
            ModerationTargetType.NICKNAME,
            participant.user_id or participant.id,
            participant.display_name,
            participant.user_id,
        )

    def _nickname_of_player(self, player_id: uuid.UUID) -> ReportedContent:
        player: GamePlayer | None = game_repository.get_game_player(self._session, player_id)
        if player is None:
            raise ReportTargetNotFoundError
        return ReportedContent(
            ModerationTargetType.NICKNAME,
            player.user_id or player.id,
            player.display_name,
            player.user_id,
        )

    def _closed_game(self, game_id: uuid.UUID) -> ReportedContent:
        game: Game | None = game_repository.get_game(self._session, game_id)
        if game is None or game.status is not GameStatus.CLOSED or game.hidden_at is not None:
            raise ReportTargetNotFoundError
        return ReportedContent(
            ModerationTargetType.GAME, game.id, game.snapshot.name, game.admin_id
        )
