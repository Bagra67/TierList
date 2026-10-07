"""Colonnes communes des modèles, partagées par héritage (mixins SQLAlchemy).

Un mixin par besoin plutôt qu'une classe de base unique : chaque modèle prend ceux qui le
concernent. SoftDeleteMixin surtout ne va pas partout, car une table supprimée logiquement
oblige chaque requête à filtrer deleted_at.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # onupdate ne voit que les UPDATE de la ligne elle-même : un changement dans une table liée
    # (ex. une tuile d'un template) doit mettre la date à jour explicitement.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    # None tant que la ligne n'est pas supprimée logiquement
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
