import logging
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_guest_token
from app.models.enums import GameStatus, ModerationTargetType, ReportReason
from app.models.game import Game
from app.models.image import Image, ImageStatus
from app.models.report import Report
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.seed.sizes import SeedSize
from app.services.moderation_log import ModerationLogService
from app.services.report_queue import ReportQueueService

logger = logging.getLogger(__name__)

REPORTS_SPAN_DAYS = 14
EVERY_NTH_REPORT_IS_ANONYMOUS = 3
OTHER_REASON_DETAILS = "Ce contenu semble copié sans autorisation."
HIDE_GAME_REASON = "Partie masquée : contenu contraire aux règles."
DISMISS_REASON = "Rien de contraire aux règles."


@dataclass(frozen=True)
class _Content:
    target_type: ModerationTargetType
    target_id: uuid.UUID
    label: str | None
    owner_id: uuid.UUID | None


@dataclass(frozen=True)
class SeedReports:
    reports: int
    moderation_actions: int


def create_reports(
    session: Session,
    settings: Settings,
    size: SeedSize,
    super_admins: list[User],
    players: list[User],
    rng: random.Random,
) -> SeedReports:
    player_ids: list[uuid.UUID] = [player.id for player in players]
    game_to_hide: _Content = _oldest_closed_game(session, player_ids)
    games: list[_Content] = _closed_games(session, player_ids, size.reported_games + 1)
    other_games: list[_Content] = [
        game for game in games if game.target_id != game_to_hide.target_id
    ][: size.reported_games]
    contents: list[_Content] = [
        *_visible_images(session, player_ids, size.reported_images),
        *_nicknames(players, size.reported_nicknames, rng),
        *other_games,
        game_to_hide,
    ]
    reports: list[Report] = []
    for content_index, content in enumerate(contents):
        reporter_count: int = size.reports_on_most_reported_content if content_index == 0 else 1
        reporter_ids: list[uuid.UUID] = [
            player_id for player_id in player_ids if player_id != content.owner_id
        ]
        for report_index, reporter_id in enumerate(rng.sample(reporter_ids, reporter_count)):
            anonymous: bool = (report_index + 1) % EVERY_NTH_REPORT_IS_ANONYMOUS == 0
            reports.append(
                _report(
                    content, None if anonymous else reporter_id, content_index, report_index, rng
                )
            )
    session.add_all(reports)
    session.commit()
    logger.info("Signalements : %d sur %d contenus", len(reports), len(contents))
    queue: ReportQueueService = ReportQueueService(
        session, settings, ModerationLogService(session, settings)
    )
    queue.hide_game(rng.choice(super_admins), game_to_hide.target_id, HIDE_GAME_REASON)
    dismissed: _Content = other_games[-1]
    queue.dismiss(
        rng.choice(super_admins), dismissed.target_type, dismissed.target_id, DISMISS_REASON
    )
    logger.info("Signalements traités : une partie masquée, une partie classée")
    return SeedReports(reports=len(reports), moderation_actions=2)


def _report(
    content: _Content,
    reporter_id: uuid.UUID | None,
    content_index: int,
    report_index: int,
    rng: random.Random,
) -> Report:
    reason: ReportReason = rng.choice(list(ReportReason))
    return Report(
        created_at=datetime.now(UTC) - timedelta(days=rng.uniform(0, REPORTS_SPAN_DAYS)),
        reporter_id=reporter_id,
        reporter_browser_hash=(
            hash_guest_token(f"seed-browser-{content_index}-{report_index}")
            if reporter_id is None
            else None
        ),
        target_type=content.target_type,
        target_id=content.target_id,
        target_label=content.label,
        owner_id=content.owner_id,
        reason=reason,
        details=OTHER_REASON_DETAILS if reason is ReportReason.OTHER else None,
    )


def _visible_images(session: Session, player_ids: list[uuid.UUID], count: int) -> list[_Content]:
    statement: Select[uuid.UUID, uuid.UUID | None] = (
        select(Image.id, Image.owner_id)
        .where(Image.status == ImageStatus.VISIBLE, Image.owner_id.in_(player_ids))
        .order_by(Image.id)
        .limit(count)
    )
    return [
        _Content(ModerationTargetType.IMAGE, image_id, None, owner_id)
        for image_id, owner_id in session.execute(statement).all()
    ]


def _nicknames(players: list[User], count: int, rng: random.Random) -> list[_Content]:
    return [
        _Content(ModerationTargetType.NICKNAME, player.id, player.display_name, player.id)
        for player in rng.sample(players, count)
    ]


def _oldest_closed_game(session: Session, player_ids: list[uuid.UUID]) -> _Content:
    statement: Select[uuid.UUID, str, uuid.UUID | None] = (
        select(Game.id, TemplateSnapshot.name, Game.admin_id)
        .join(TemplateSnapshot, TemplateSnapshot.id == Game.snapshot_id)
        .where(Game.status == GameStatus.CLOSED, Game.admin_id.in_(player_ids))
        .order_by(Game.closed_at, Game.id)
        .limit(1)
    )
    game_id, name, admin_id = session.execute(statement).one()
    return _Content(ModerationTargetType.GAME, game_id, name, admin_id)


def _closed_games(session: Session, player_ids: list[uuid.UUID], count: int) -> list[_Content]:
    statement: Select[uuid.UUID, str, uuid.UUID | None] = (
        select(Game.id, TemplateSnapshot.name, Game.admin_id)
        .join(TemplateSnapshot, TemplateSnapshot.id == Game.snapshot_id)
        .where(Game.status == GameStatus.CLOSED, Game.admin_id.in_(player_ids))
        .order_by(Game.id)
        .limit(count)
    )
    return [
        _Content(ModerationTargetType.GAME, game_id, name, admin_id)
        for game_id, name, admin_id in session.execute(statement).all()
    ]
