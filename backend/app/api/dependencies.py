from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.exceptions.auth import InvalidAccessTokenError
from app.exceptions.http import AppHTTPException
from app.models.user import User
from app.services.auth import AuthenticatedSession, AuthService
from app.services.email import EmailSender
from app.services.google_oauth import GoogleOAuthClient
from app.services.templates import TemplateService

# auto_error=False : l'absence de token est traitée ci-dessous, avec une 401 au format ErrorResponse
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings)


def get_template_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TemplateService:
    return TemplateService(session, settings)


def get_email_sender(settings: Annotated[Settings, Depends(get_settings)]) -> EmailSender:
    # Remplacé par un faux dans les tests : aucun email n'est réellement envoyé
    return EmailSender(settings)


def get_google_oauth_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleOAuthClient | None:
    """Client Google, ou None si la connexion avec Google n'est pas configurée."""
    if settings.google_client_id is None or settings.google_client_secret is None:
        return None
    return GoogleOAuthClient(
        settings.google_client_id,
        settings.google_client_secret.get_secret_value(),
        settings.google_redirect_uri,
        http_timeout_seconds=settings.google_http_timeout_seconds,
    )


def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedSession:
    """Session authentifiée par l'access token (en-tête Authorization: Bearer), sinon 401."""
    unauthorized = AppHTTPException(
        status_code=401,
        code=ErrorCode.NOT_AUTHENTICATED,
        detail=messages.NOT_AUTHENTICATED,
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        session = service.authenticate_access_token(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise unauthorized from exc
    if session is None:
        raise unauthorized
    return session


def get_current_user(
    session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> User:
    """Utilisateur authentifié : la dépendance à utiliser pour protéger une route."""
    return session.user
