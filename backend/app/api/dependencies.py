from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import InvalidAccessTokenError
from app.db.session import get_db_session
from app.models.user import User
from app.services.auth import AuthenticatedSession, AuthService

# auto_error=False : l'absence de token est traitée ci-dessous, avec une 401 au format ErrorResponse
bearer_scheme = HTTPBearer(auto_error=False)

NOT_AUTHENTICATED_DETAIL = "Authentification requise"


def get_auth_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings)


def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedSession:
    """Session authentifiée par l'access token (en-tête Authorization: Bearer), sinon 401."""
    unauthorized = HTTPException(
        status_code=401,
        detail=NOT_AUTHENTICATED_DETAIL,
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
