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
    email: EmailStr
    password: NewPassword
    display_name: DisplayName
    language: Language = DEFAULT_EMAIL_LANGUAGE


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    has_password: bool
    email_verified: bool
    role: UserRole
    created_at: datetime


class DeleteAccountRequest(BaseModel):
    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)


class EmailVerificationRequest(BaseModel):
    language: Language = DEFAULT_EMAIL_LANGUAGE


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    language: Language = DEFAULT_EMAIL_LANGUAGE


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)
    password: NewPassword
