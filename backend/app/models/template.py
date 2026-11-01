import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.moderation import MODERATION_REASON_MAX_LENGTH
from app.constants.templates import FREE_PLAN_MAX_TILES, TEMPLATE_NAME_MAX_LENGTH
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import text_enum
from app.models.enums import TemplateModeration

if TYPE_CHECKING:
    from app.models.tier import Tier
    from app.models.tile import Tile


class Template(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Ce qu'on classe : ses tiers et ses tuiles. Privé à son propriétaire.

    updated_at est la « dernière modification » montrée à l'utilisateur : le service doit
    aussi la mettre à jour quand un de ses tiers ou une de ses tuiles change. Supprimé logiquement
    (deleted_at), un template disparaît pour son propriétaire, puis est purgé définitivement
    après DELETED_TEMPLATE_RETENTION_DAYS.
    """

    __tablename__ = "templates"

    # Supprimer le compte supprime ses templates, même ceux déjà supprimés logiquement
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(TEMPLATE_NAME_MAX_LENGTH))
    # Décision d'un super admin (#268) : un modèle masqué ne lance plus de partie
    moderation: Mapped[TemplateModeration] = mapped_column(
        text_enum(TemplateModeration, "template_moderation"),
        default=TemplateModeration.NONE,
        server_default=text("'none'"),
    )
    # Motif du masquage, montré au propriétaire. Copié ici : le journal de modération est purgé
    # après 3 ans, un modèle peut rester masqué plus longtemps
    moderation_reason: Mapped[str | None] = mapped_column(String(MODERATION_REASON_MAX_LENGTH))

    tiers: Mapped[list[Tier]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tier.position"
    )
    tiles: Mapped[list[Tile]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="Tile.position"
    )

    @property
    def max_tiles(self) -> int:
        """Nombre maximal de tuiles. Tout est gratuit pour l'instant : la limite dépendra du plan
        du propriétaire quand les plans payants arriveront."""
        return FREE_PLAN_MAX_TILES
