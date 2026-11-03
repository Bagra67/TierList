import uuid
from datetime import datetime


class InvalidAccessTokenError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class IncorrectPasswordError(Exception):
    pass


class GoogleEmailNotVerifiedError(Exception):
    pass


class InvalidEmailTokenError(Exception):
    pass


class ReauthenticationRequiredError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class AccountBannedError(Exception):
    def __init__(self, user_id: uuid.UUID, reason: str, ends_at: datetime | None) -> None:
        super().__init__(reason)
        self.user_id = user_id
        self.reason = reason
        self.ends_at = ends_at


class InvalidBanNoticeError(Exception):
    pass
