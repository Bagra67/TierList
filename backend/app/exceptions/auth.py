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


class ReauthenticationRequiredError(Exception):
    """Compte sans mot de passe dont la dernière connexion est trop ancienne pour confirmer."""
