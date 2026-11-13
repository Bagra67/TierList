import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field
from pydantic_core import PydanticCustomError

from app.constants import messages
from app.constants.auth import (
    EMAIL_TOKEN_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
)
from app.constants.i18n import DEFAULT_EMAIL_LANGUAGE, Language
from app.core.config import get_settings
from app.models.enums import UserRole
from app.schemas.common import DisplayName


def _check_password_length(password: str) -> str:
    min_length = get_settings().password_min_length
    if len(password) < min_length:
        raise PydanticCustomError(
            "password_too_short",
            messages.PASSWORD_TOO_SHORT,
            {"min_length": min_length},
        )
    return password


NewPassword = Annotated[
    str, Field(max_length=PASSWORD_MAX_LENGTH), AfterValidator(_check_password_length)
]


class RegisterRequest(BaseModel):
    """Sign-up with an email and a password; `language` chooses the language of the verification
    email."""

    email: EmailStr
    password: NewPassword
    display_name: DisplayName
    language: Language = DEFAULT_EMAIL_LANGUAGE


class LoginRequest(BaseModel):
    """Sign-in with an email and a password."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    """Access token to send in the `Authorization: Bearer` header, valid for `expires_in` seconds.
    The refresh token is never in the body: it is in an HttpOnly cookie."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """An account, as its owner sees it. `has_password` is false as long as the account has no
    password (a Google account that never set one)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    has_password: bool
    email_verified: bool
    role: UserRole
    created_at: datetime


class DeleteAccountRequest(BaseModel):
    """Confirmation of the account deletion: the password, required for an account that has one,
    absent for an account without a password."""

    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)


class EmailVerificationRequest(BaseModel):
    """Language of the new verification email."""

    language: Language = DEFAULT_EMAIL_LANGUAGE


class VerifyEmailRequest(BaseModel):
    """Token of the verification link received by email."""

    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)


class ForgotPasswordRequest(BaseModel):
    """Address of the account, and language of the reset email."""

    email: EmailStr
    language: Language = DEFAULT_EMAIL_LANGUAGE


class ResetPasswordRequest(BaseModel):
    """Token of the reset link received by email, and the new password."""

    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)
    password: NewPassword
