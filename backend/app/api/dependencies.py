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
from app.services.account_bans import AccountBanService
from app.services.account_review import AccountReviewService
from app.services.auth import AuthenticatedSession, AuthService
from app.services.email import EmailSender
from app.services.game_results import GameResultsService
from app.services.games import GameService
from app.services.google_oauth import GoogleOAuthClient
from app.services.history import HistoryService
from app.services.image_moderation import ImageModerationService
from app.services.image_storage import ImageStorage, create_image_storage
from app.services.images import ImageService
from app.services.moderation_log import ModerationLogService
from app.services.recent_uploads import RecentUploadsService
from app.services.room_channel import ConnectionRegistry, RoomEventPublisher, room_connections
from app.services.rooms import RoomService, RoomViewer
from app.services.round_timers import RoundScheduler, round_timers
from app.services.template_moderation import TemplateModerationService
from app.services.templates import TemplateService

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
    return lambda: Session(get_engine())


def get_connection_registry() -> ConnectionRegistry:
    return room_connections


def get_room_event_publisher(
    registry: Annotated[ConnectionRegistry, Depends(get_connection_registry)],
) -> RoomEventPublisher:
    return registry


def get_round_scheduler() -> RoundScheduler:
    return round_timers


def get_room_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    publisher: Annotated[RoomEventPublisher, Depends(get_room_event_publisher)],
) -> RoomService:
    return RoomService(session, settings, publisher)


def get_moderation_log_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ModerationLogService:
    return ModerationLogService(session, settings)


def get_template_moderation_service(
    session: Annotated[Session, Depends(get_db_session)],
    moderation_log: Annotated[ModerationLogService, Depends(get_moderation_log_service)],
) -> TemplateModerationService:
    return TemplateModerationService(session, moderation_log)


def get_recent_uploads_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> RecentUploadsService:
    return RecentUploadsService(session)


def get_history_service(session: Annotated[Session, Depends(get_db_session)]) -> HistoryService:
    return HistoryService(session)


def get_game_results_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> GameResultsService:
    return GameResultsService(session)


def build_game_service(
    session: Session, settings: Settings, publisher: RoomEventPublisher, scheduler: RoundScheduler
) -> GameService:
    rooms: RoomService = RoomService(session, settings, publisher)
    return GameService(session, publisher, rooms, TemplateService(session, settings), scheduler)


def get_game_service(
    session: Annotated[Session, Depends(get_db_session)],
    publisher: Annotated[RoomEventPublisher, Depends(get_room_event_publisher)],
    rooms: Annotated[RoomService, Depends(get_room_service)],
    templates: Annotated[TemplateService, Depends(get_template_service)],
    scheduler: Annotated[RoundScheduler, Depends(get_round_scheduler)],
) -> GameService:
    return GameService(session, publisher, rooms, templates, scheduler)


def get_image_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ImageStorage:
    return create_image_storage(settings)


def get_image_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
) -> ImageService:
    return ImageService(session, settings, storage)


def get_image_moderation_service(
    session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[ImageStorage, Depends(get_image_storage)],
    moderation_log: Annotated[ModerationLogService, Depends(get_moderation_log_service)],
) -> ImageModerationService:
    return ImageModerationService(session, storage, moderation_log)


def get_account_ban_service(
    session: Annotated[Session, Depends(get_db_session)],
    moderation_log: Annotated[ModerationLogService, Depends(get_moderation_log_service)],
) -> AccountBanService:
    return AccountBanService(session, moderation_log)


def get_account_review_service(
    session: Annotated[Session, Depends(get_db_session)],
    templates: Annotated[TemplateService, Depends(get_template_service)],
    image_moderation: Annotated[ImageModerationService, Depends(get_image_moderation_service)],
) -> AccountReviewService:
    return AccountReviewService(session, templates, image_moderation)


def get_email_sender(settings: Annotated[Settings, Depends(get_settings)]) -> EmailSender:
    return EmailSender(settings)


def get_google_oauth_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleOAuthClient | None:
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
    return session.user


def get_current_super_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_super_admin:
        raise AppHTTPException(
            status_code=403,
            code=ErrorCode.SUPER_ADMIN_REQUIRED,
            detail=messages.SUPER_ADMIN_REQUIRED,
        )
    return user


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


SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentSessionDep = Annotated[AuthenticatedSession, Depends(get_current_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
SuperAdminDep = Annotated[User, Depends(get_current_super_admin)]
RoomViewerDep = Annotated[RoomViewer, Depends(get_room_viewer)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
GameServiceDep = Annotated[GameService, Depends(get_game_service)]
GameResultsServiceDep = Annotated[GameResultsService, Depends(get_game_results_service)]
HistoryServiceDep = Annotated[HistoryService, Depends(get_history_service)]
ModerationLogServiceDep = Annotated[ModerationLogService, Depends(get_moderation_log_service)]
ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
TemplateModerationServiceDep = Annotated[
    TemplateModerationService, Depends(get_template_moderation_service)
]
AccountBanServiceDep = Annotated[AccountBanService, Depends(get_account_ban_service)]
AccountReviewServiceDep = Annotated[AccountReviewService, Depends(get_account_review_service)]
RecentUploadsServiceDep = Annotated[RecentUploadsService, Depends(get_recent_uploads_service)]
ImageModerationServiceDep = Annotated[ImageModerationService, Depends(get_image_moderation_service)]
ImageStorageDep = Annotated[ImageStorage, Depends(get_image_storage)]
EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
GoogleClientDep = Annotated[GoogleOAuthClient | None, Depends(get_google_oauth_client)]
SessionFactoryDep = Annotated[SessionFactory, Depends(get_session_factory)]
PublisherDep = Annotated[RoomEventPublisher, Depends(get_room_event_publisher)]
RegistryDep = Annotated[ConnectionRegistry, Depends(get_connection_registry)]
RoundSchedulerDep = Annotated[RoundScheduler, Depends(get_round_scheduler)]
