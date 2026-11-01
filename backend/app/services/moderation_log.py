"""Journal de modération (US-1.9, docs/technical/moderation.md) : chaque action d'un super admin y
est écrite, dans la même transaction que l'action elle-même."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.moderation_action import ModerationAction
from app.models.user import User
from app.repositories import moderation_actions as moderation_action_repository

logger = logging.getLogger(__name__)


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
        """Écrit une entrée, sans valider la transaction : c'est l'action de modération qui la
        valide, pour que l'action et sa trace réussissent ou échouent ensemble. Les noms sont
        copiés : ils restent lisibles après la suppression du compte ou de la cible."""
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

    def purge_expired(self) -> int:
        """Supprime les entrées plus anciennes que la durée de conservation ; renvoie leur
        nombre. Le seul endroit où une entrée est supprimée."""
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
