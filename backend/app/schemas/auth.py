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
    """Inscription par e-mail et mot de passe ; `language` choisit la langue de l'e-mail de
    vérification."""

    email: EmailStr
    password: NewPassword
    display_name: DisplayName
    language: Language = DEFAULT_EMAIL_LANGUAGE


class LoginRequest(BaseModel):
    """Connexion par e-mail et mot de passe."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    """Access token à envoyer dans l'en-tête `Authorization: Bearer`, valable `expires_in`
    secondes. Le refresh token n'est jamais dans le corps : il est dans un cookie HttpOnly."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Un compte, tel que son propriétaire le voit. `has_password` est faux tant que le compte n'a
    pas de mot de passe (compte Google qui n'en a jamais défini)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    has_password: bool
    email_verified: bool
    role: UserRole
    created_at: datetime


class DeleteAccountRequest(BaseModel):
    """Confirmation de la suppression du compte : le mot de passe, obligatoire pour un compte qui
    en a un, absent pour un compte sans mot de passe."""

    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)


class EmailVerificationRequest(BaseModel):
    """Langue du nouvel e-mail de vérification."""

    language: Language = DEFAULT_EMAIL_LANGUAGE


class VerifyEmailRequest(BaseModel):
    """Token du lien de vérification reçu par e-mail."""

    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)


class ForgotPasswordRequest(BaseModel):
    """Adresse du compte, et langue de l'e-mail de réinitialisation."""

    email: EmailStr
    language: Language = DEFAULT_EMAIL_LANGUAGE


class ResetPasswordRequest(BaseModel):
    """Token du lien de réinitialisation reçu par e-mail, et nouveau mot de passe."""

    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)
    password: NewPassword
