import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.moderation_action import ModerationAction
from app.models.user import User
from app.repositories import moderation_actions as moderation_action_repository
from app.repositories import users as user_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModerationLogPage:
    entries: list[ModerationAction]
    has_more: bool


class ModerationLogService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def record(
        self,
        actor: User,
        action: ModerationActionKind,
        target_type: ModerationTargetType,
        target_id: uuid.UUID | None,
        target_label: str,
        reason: str,
    ) -> ModerationAction:
        moderation_action: ModerationAction = ModerationAction(
            actor_id=actor.id,
            actor_name=actor.display_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            reason=reason,
        )
        moderation_action_repository.add_moderation_action(self._session, moderation_action)
        self._session.flush()
        return moderation_action

    def page(
        self,
        limit: int,
        offset: int,
        actor_id: uuid.UUID | None,
        target: str | None,
        account_id: uuid.UUID | None = None,
    ) -> ModerationLogPage:
        entries: list[ModerationAction] = moderation_action_repository.list_moderation_actions(
            self._session, limit + 1, offset, actor_id, target, account_id
        )
        return ModerationLogPage(entries=entries[:limit], has_more=len(entries) > limit)

    def super_admins(self) -> list[User]:
        return user_repository.list_super_admins(self._session)

    def purge_expired(self) -> int:
        limit: datetime = datetime.now(UTC) - timedelta(
            days=self._settings.moderation_log_retention_days
        )
        purged: int = moderation_action_repository.delete_moderation_actions_before(
            self._session, limit
        )
        self._session.commit()
        logger.info(
            "Journal de modération purgé : %d entrées (avant %s)", purged, limit.isoformat()
        )
        return purged
