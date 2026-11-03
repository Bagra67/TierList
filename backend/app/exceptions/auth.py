import uuid
from datetime import datetime


class InvalidAccessTokenError(Exception):
    """Access token absent, mal formé, falsifié, expiré ou d'un autre type."""


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class IncorrectPasswordError(Exception):
    pass


class GoogleEmailNotVerifiedError(Exception):
    """Google ne garantit pas que l'adresse appartient à ce compte : elle ne peut servir."""


class InvalidEmailTokenError(Exception):
    """Lien envoyé par email mal formé, falsifié, expiré, ou qui ne correspond plus au compte."""


class ReauthenticationRequiredError(Exception):
    """Compte sans mot de passe dont la dernière connexion est trop ancienne pour confirmer."""


class UserNotFoundError(Exception):
    """Aucun compte avec cette adresse."""


class AccountBannedError(Exception):
    """Compte banni par un super admin (US-1.8) : la connexion est refusée, avec le motif et,
    pour un bannissement temporaire, sa fin."""

    def __init__(self, user_id: uuid.UUID, reason: str, ends_at: datetime | None) -> None:
        super().__init__(reason)
        self.user_id = user_id
        self.reason = reason
        self.ends_at = ends_at


class InvalidBanNoticeError(Exception):
    """Cookie du motif d'un bannissement mal formé, falsifié ou expiré."""
