from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.rooms import GUEST_COOKIE
from app.core.config import Settings, get_settings
from app.db.session import get_db_session, get_engine
from app.exceptions.auth import InvalidAccessTokenError
from app.exceptions.http import AppHTTPException
from app.models.user import User
from app.services.auth import AuthenticatedSession, AuthService
from app.services.email import EmailSender
from app.services.games import GameService
from app.services.google_oauth import GoogleOAuthClient
from app.services.image_storage import ImageStorage, create_image_storage
from app.services.images import ImageService
from app.services.room_channel import ConnectionRegistry, RoomEventPublisher, room_connections
from app.services.rooms import RoomService, RoomViewer
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


# Ouvre une session courte : le canal temps réel vit longtemps, il ne garde pas de connexion à
# la base entre deux accès
SessionFactory = Callable[[], AbstractContextManager[Session]]


def get_session_factory() -> SessionFactory:
    # Remplacée dans les tests : les accès du canal y passent par la session du test
    return lambda: Session(get_engine())


def get_connection_registry() -> ConnectionRegistry:
    # Les sockets ouverts de ce processus
    return room_connections


def get_room_event_publisher(
    registry: Annotated[ConnectionRegistry, Depends(get_connection_registry)],
) -> RoomEventPublisher:
    # Les services publient vers les sockets du registre ; remplaçable dans les tests
    return registry


def get_room_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    publisher: Annotated[RoomEventPublisher, Depends(get_room_event_publisher)],
) -> RoomService:
    return RoomService(session, settings, publisher)


def get_game_service(
    session: Annotated[Session, Depends(get_db_session)],
    publisher: Annotated[RoomEventPublisher, Depends(get_room_event_publisher)],
    rooms: Annotated[RoomService, Depends(get_room_service)],
    templates: Annotated[TemplateService, Depends(get_template_service)],
) -> GameService:
    # FastAPI met la session en cache par requête : les trois services partagent la même
    return GameService(session, publisher, rooms, templates)


def get_image_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ImageStorage:
    # Remplacé par un faux dans les tests d'API : seuls les tests du stockage contactent S3
    return create_image_storage(settings)


def get_image_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> ImageService:
    return ImageService(session, settings, storage)


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


def get_room_viewer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    guest_token: Annotated[str | None, Cookie(alias=GUEST_COOKIE)] = None,
) -> RoomViewer:
    """Lecteur d'une salle : un compte s'il envoie un access token (vérifié comme partout : un
    token invalide répond 401, pour que le frontend rafraîchisse sa session), sinon peut-être un
    invité, reconnu par le cookie de sa salle. Sans les deux, la salle répondra 404."""
    if credentials is not None:
        session: AuthenticatedSession = get_current_session(credentials, service)
        return RoomViewer(user=session.user, guest_token=None)
    return RoomViewer(user=None, guest_token=guest_token)
