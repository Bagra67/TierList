import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH
from app.constants.moderation import (
    MODERATION_REASON_MAX_LENGTH,
    MODERATION_TARGET_LABEL_MAX_LENGTH,
)
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import ModerationActionKind, ModerationTargetType


class ModerationAction(UUIDPrimaryKeyMixin, Base):
    """Une entrée du journal de modération (US-1.9) : quel super admin a fait quoi, sur quoi,
    quand et pourquoi. Jamais modifiée ni supprimée, sauf par la purge des entrées expirées
    (MODERATION_LOG_RETENTION_DAYS, docs/technical/moderation.md)."""

    __tablename__ = "moderation_actions"

    # Pas de TimestampMixin : une entrée ne change jamais, elle n'a pas d'updated_at.
    # clock_timestamp() pour la même raison que TimestampMixin. Indexé : le journal est trié dessus
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), index=True
    )
    # SET NULL : supprimer le compte du super admin garde l'entrée, avec son nom (actor_name)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Nom du super admin au moment de l'action
    actor_name: Mapped[str] = mapped_column(String(DISPLAY_NAME_MAX_LENGTH))
    action: Mapped[ModerationActionKind] = mapped_column(
        text_enum(ModerationActionKind, "moderation_action_kind")
    )
    target_type: Mapped[ModerationTargetType] = mapped_column(
        text_enum(ModerationTargetType, "moderation_target_type")
    )
    # Pas de clé étrangère : la cible (modèle, image, compte…) peut être supprimée, l'entrée reste
    target_id: Mapped[uuid.UUID | None]
    # Libellé de la cible au moment de l'action, lisible même une fois la cible supprimée
    target_label: Mapped[str] = mapped_column(String(MODERATION_TARGET_LABEL_MAX_LENGTH))
    reason: Mapped[str] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))
