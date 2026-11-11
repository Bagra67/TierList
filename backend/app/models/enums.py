from enum import StrEnum


class RoomStatus(StrEnum):
    """Une salle fermée n'est pas gardée (docs/product/milestone-1/lifecycles.md) : elle est
    supprimée, il n'y a donc pas de statut « fermée »."""

    OPEN = "open"
    PLAYING = "playing"


class GameStatus(StrEnum):
    """Cycle de vie d'une partie (docs/product/milestone-1/lifecycles.md)."""

    IN_ROUND = "in_round"
    COOLDOWN = "cooldown"
    CLOSED = "closed"


class ItemOrder(StrEnum):
    """Ordre de passage des tuiles pendant une partie."""

    TEMPLATE = "template"
    RANDOM = "random"


class AutoAdvance(StrEnum):
    """Passage automatique à l'item suivant."""

    NONE = "none"
    TIMER = "timer"
    EVERYONE_PLACED = "everyone_placed"


class PlacementPhase(StrEnum):
    ROUND = "round"
    FINAL = "final"


class UserRole(StrEnum):
    """Rôle d'un compte (docs/product/milestone-2/domain-model.md). Jamais attribué par
    l'application : seulement hors de l'API (scripts/set_super_admin.py en local, une requête SQL
    en staging et en production)."""

    USER = "user"
    SUPER_ADMIN = "super_admin"


class ModerationActionKind(StrEnum):
    """Action d'un super admin, écrite au journal de modération (US-1.9)."""

    DISMISS = "dismiss"
    HIDE = "hide"
    UNHIDE = "unhide"
    DELETE = "delete"
    BAN = "ban"
    LIFT_BAN = "lift_ban"


class ModerationTargetType(StrEnum):
    """Ce sur quoi porte une action de modération : les contenus signalables (US-1.2) et le
    compte."""

    TEMPLATE = "template"
    IMAGE = "image"
    ACCOUNT = "account"
    NICKNAME = "nickname"
    GAME = "game"


class ReportTargetKind(StrEnum):
    """Ce que désigne target_id dans un signalement (US-1.2)."""

    ITEM = "item"
    PARTICIPANT = "participant"
    PLAYER = "player"
    GAME = "game"


class ReportReason(StrEnum):
    """Motif d'un signalement (US-1.2)."""

    ILLEGAL = "illegal"
    SEXUAL = "sexual"
    VIOLENCE_OR_HATE = "violence_or_hate"
    HARASSMENT = "harassment"
    SPAM = "spam"
    OTHER = "other"


class ReportStatus(StrEnum):
    OPEN = "open"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class TemplateModeration(StrEnum):
    """Décision de la modération sur un modèle (US-1.5)."""

    NONE = "none"
    HIDDEN = "hidden"


class TemplateVisibility(StrEnum):
    """Visibilité choisie par le propriétaire d'un modèle (US-2.1, US-2.3)."""

    PRIVATE = "private"
    PUBLIC = "public"
