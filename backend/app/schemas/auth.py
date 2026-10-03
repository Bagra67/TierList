import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from app.constants import messages
from app.constants.auth import (
    DISPLAY_NAME_MAX_LENGTH,
    EMAIL_TOKEN_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
)
from app.constants.i18n import DEFAULT_LANGUAGE, Language
from app.core.config import get_settings

DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH),
]


class RegisterRequest(BaseModel):
    email: EmailStr
    # Longueur minimale configurable (PASSWORD_MIN_LENGTH) : vérifiée par le validateur ci-dessous
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    display_name: DisplayName
    # Langue de l'email de vérification : celle de l'interface
    language: Language = DEFAULT_LANGUAGE

    @field_validator("password")
    @classmethod
    def check_password_length(cls, password: str) -> str:
        # Lue à chaque requête : changer PASSWORD_MIN_LENGTH ne demande qu'un redémarrage.
        # Le param min_length (repris dans la 422) permet au frontend d'afficher le minimum exact.
        min_length = get_settings().password_min_length
        if len(password) < min_length:
            raise PydanticCustomError(
                # Pydantic exige un littéral : c'est la valeur de ErrorCode.PASSWORD_TOO_SHORT
                "password_too_short",
                messages.PASSWORD_TOO_SHORT,
                {"min_length": min_length},
            )
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    # Durée de validité de l'access token, en secondes
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    # False pour un compte créé avec Google : la suppression demande alors de se reconnecter
    has_password: bool
    # Adresse confirmée par le lien reçu par email (ou par Google)
    email_verified: bool
    created_at: datetime


class DeleteAccountRequest(BaseModel):
    # Confirmation : un access token volé ne suffit pas pour supprimer le compte.
    # Absent pour un compte Google, qui confirme par une connexion récente.
    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)


class EmailVerificationRequest(BaseModel):
    language: Language = DEFAULT_LANGUAGE


class VerifyEmailRequest(BaseModel):
    # Token du lien reçu par email ; sa validité est vérifiée par le service
    token: str = Field(min_length=1, max_length=EMAIL_TOKEN_MAX_LENGTH)
