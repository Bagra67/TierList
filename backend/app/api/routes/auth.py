import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Query, Response
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    AuthServiceDep,
    CurrentSessionDep,
    CurrentUserDep,
    EmailSenderDep,
    GameServiceDep,
    GoogleClientDep,
    SettingsDep,
)
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.auth import (
    CONFIRM_PARAM,
    DELETE_ACCOUNT_STEP,
    FRONTEND_HOME,
    FRONTEND_LOGIN,
    GOOGLE_ACCESS_DENIED,
    GOOGLE_BAN_NOTICE_COOKIE,
    GOOGLE_COOKIE_SUBPATH,
    GOOGLE_ERROR_ACCOUNT_BANNED,
    GOOGLE_ERROR_CANCELLED,
    GOOGLE_ERROR_EMAIL_NOT_VERIFIED,
    GOOGLE_ERROR_FAILED,
    GOOGLE_ERROR_UNAVAILABLE,
    GOOGLE_LOGIN_COOKIE,
    LOGIN_ERROR_PARAM,
    REFRESH_TOKEN_COOKIE,
    GoogleNextStep,
)
from app.constants.error_codes import ErrorCode
from app.core.config import Settings
from app.core.errors import ErrorResponse
from app.core.security import create_ban_notice_token
from app.exceptions.auth import (
    AccountBannedError,
    EmailAlreadyRegisteredError,
    GoogleEmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidBanNoticeError,
    InvalidCredentialsError,
    InvalidEmailTokenError,
    InvalidRefreshTokenError,
    ReauthenticationRequiredError,
)
from app.exceptions.google import GoogleAuthError
from app.exceptions.http import AppHTTPException
from app.schemas.auth import (
    DeleteAccountRequest,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import IssuedTokens
from app.services.google_oauth import GoogleLoginAttempt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshTokenCookie = Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)]


def _set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=int(timedelta(days=settings.refresh_token_ttl_days).total_seconds()),
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _account_banned(exc: AccountBannedError) -> AppHTTPException:
    if exc.ends_at is None:
        return AppHTTPException(
            status_code=403,
            code=ErrorCode.ACCOUNT_BANNED,
            detail=messages.ACCOUNT_BANNED.format(reason=exc.reason),
            params={"reason": exc.reason},
        )
    ends_at: str = exc.ends_at.isoformat()
    return AppHTTPException(
        status_code=403,
        code=ErrorCode.ACCOUNT_BANNED_UNTIL,
        detail=messages.ACCOUNT_BANNED_UNTIL.format(ends_at=ends_at, reason=exc.reason),
        params={"reason": exc.reason, "ends_at": ends_at},
    )


def _session_expired(settings: Settings) -> AppHTTPException:
    cleared = Response()
    _clear_refresh_cookie(cleared, settings)
    return AppHTTPException(
        status_code=401,
        code=ErrorCode.SESSION_EXPIRED,
        detail=messages.SESSION_EXPIRED,
        headers={"set-cookie": cleared.headers["set-cookie"]},
    )


def _token_response(response: Response, tokens: IssuedTokens, settings: Settings) -> TokenResponse:
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return TokenResponse(
        access_token=tokens.access_token, expires_in=tokens.access_token_expires_in
    )


@router.post(
    "/register",
    status_code=201,
    responses={
        409: {"model": ErrorResponse, "description": messages.EMAIL_ALREADY_REGISTERED_DESCRIPTION}
    },
)
def register(
    payload: RegisterRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    service: AuthServiceDep,
    email_sender: EmailSenderDep,
    settings: SettingsDep,
) -> TokenResponse:
    try:
        registration = service.register(
            payload.email, payload.password, payload.display_name, payload.language
        )
    except EmailAlreadyRegisteredError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.EMAIL_ALREADY_REGISTERED,
            detail=messages.EMAIL_ALREADY_REGISTERED,
        ) from exc
    background_tasks.add_task(email_sender.send, registration.verification_email)
    return _token_response(response, registration.tokens, settings)


@router.post(
    "/login",
    responses={
        **UNAUTHORIZED_RESPONSE,
        403: {"model": ErrorResponse, "description": messages.ACCOUNT_BANNED_DESCRIPTION},
    },
)
def login(
    payload: LoginRequest, response: Response, service: AuthServiceDep, settings: SettingsDep
) -> TokenResponse:
    try:
        tokens = service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise AppHTTPException(
            status_code=401,
            code=ErrorCode.INVALID_CREDENTIALS,
            detail=messages.INVALID_CREDENTIALS,
        ) from exc
    except AccountBannedError as exc:
        raise _account_banned(exc) from exc
    return _token_response(response, tokens, settings)


@router.post("/refresh", responses=UNAUTHORIZED_RESPONSE)
def refresh(
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: RefreshTokenCookie = None,
) -> TokenResponse:
    if refresh_token is None:
        raise _session_expired(settings)
    try:
        tokens = service.refresh(refresh_token)
    except InvalidRefreshTokenError as exc:
        raise _session_expired(settings) from exc
    return _token_response(response, tokens, settings)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: RefreshTokenCookie = None,
) -> None:
    if refresh_token is not None:
        service.logout(refresh_token)
    _clear_refresh_cookie(response, settings)


@router.get("/me", responses=UNAUTHORIZED_RESPONSE)
def me(user: CurrentUserDep) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/email/verification", status_code=204, responses=UNAUTHORIZED_RESPONSE)
def request_email_verification(
    payload: EmailVerificationRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUserDep,
    service: AuthServiceDep,
    email_sender: EmailSenderDep,
) -> None:
    """Renvoie l'email de vérification ; sans effet si l'adresse est déjà confirmée, ou si le
    précédent email est trop récent (EMAIL_COOLDOWN_SECONDS)."""
    email_to_send = service.request_email_verification(user, payload.language)
    if email_to_send is not None:
        background_tasks.add_task(email_sender.send, email_to_send)


@router.post(
    "/email/verify",
    status_code=204,
    responses={400: {"model": ErrorResponse, "description": messages.INVALID_TOKEN_DESCRIPTION}},
)
def verify_email(payload: VerifyEmailRequest, service: AuthServiceDep) -> None:
    """Confirme l'adresse email avec le token du lien reçu ; sans session : le lien peut être
    ouvert dans un autre navigateur."""
    try:
        service.verify_email(payload.token)
    except InvalidEmailTokenError as exc:
        raise AppHTTPException(
            status_code=400, code=ErrorCode.INVALID_TOKEN, detail=messages.INVALID_TOKEN
        ) from exc


@router.delete(
    "/me",
    status_code=204,
    responses={
        **UNAUTHORIZED_RESPONSE,
        403: {"model": ErrorResponse, "description": messages.DELETE_ACCOUNT_FORBIDDEN_DESCRIPTION},
    },
)
def delete_me(
    payload: DeleteAccountRequest,
    response: Response,
    session: CurrentSessionDep,
    service: AuthServiceDep,
    games: GameServiceDep,
    settings: SettingsDep,
) -> None:
    try:
        service.delete_account(session, payload.password, before_delete=games.close_rooms_of_admin)
    except IncorrectPasswordError as exc:
        raise AppHTTPException(
            status_code=403,
            code=ErrorCode.INCORRECT_PASSWORD,
            detail=messages.INCORRECT_PASSWORD,
        ) from exc
    except ReauthenticationRequiredError as exc:
        raise AppHTTPException(
            status_code=403,
            code=ErrorCode.REAUTHENTICATION_REQUIRED,
            detail=messages.REAUTHENTICATION_REQUIRED,
        ) from exc
    _clear_refresh_cookie(response, settings)


def _google_cookie_path(settings: Settings) -> str:
    return f"{settings.auth_cookie_path}{GOOGLE_COOKIE_SUBPATH}"


def _google_redirect(location: str, settings: Settings) -> RedirectResponse:
    response = RedirectResponse(location, status_code=302)
    response.delete_cookie(
        GOOGLE_LOGIN_COOKIE,
        path=_google_cookie_path(settings),
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


def _google_failure(error_code: str, settings: Settings) -> RedirectResponse:
    return _google_redirect(f"{FRONTEND_LOGIN}?{LOGIN_ERROR_PARAM}={error_code}", settings)


def _google_account_banned(exc: AccountBannedError, settings: Settings) -> RedirectResponse:
    response = _google_failure(GOOGLE_ERROR_ACCOUNT_BANNED, settings)
    ttl = timedelta(minutes=settings.google_login_attempt_ttl_minutes)
    response.set_cookie(
        GOOGLE_BAN_NOTICE_COOKIE,
        create_ban_notice_token(
            user_id=exc.user_id,
            secret_key=settings.jwt_secret_key.get_secret_value(),
            ttl=ttl,
        ),
        max_age=int(ttl.total_seconds()),
        path=_google_cookie_path(settings),
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/google/login", status_code=302, response_class=RedirectResponse)
def google_login(
    settings: SettingsDep,
    google: GoogleClientDep,
    next_step: Annotated[GoogleNextStep | None, Query(alias="next")] = None,
) -> RedirectResponse:
    """Envoie le navigateur sur la page de connexion de Google."""
    if google is None:
        return _google_failure(GOOGLE_ERROR_UNAVAILABLE, settings)
    attempt = GoogleLoginAttempt.start(next_step)
    attempt_ttl = timedelta(minutes=settings.google_login_attempt_ttl_minutes)
    response = RedirectResponse(google.authorization_url(attempt), status_code=302)
    response.set_cookie(
        GOOGLE_LOGIN_COOKIE,
        attempt.to_cookie(settings.jwt_secret_key.get_secret_value(), attempt_ttl),
        max_age=int(attempt_ttl.total_seconds()),
        path=_google_cookie_path(settings),
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/google/callback", status_code=302, response_class=RedirectResponse)
def google_callback(
    settings: SettingsDep,
    google: GoogleClientDep,
    service: AuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    login_cookie: Annotated[str | None, Cookie(alias=GOOGLE_LOGIN_COOKIE)] = None,
) -> RedirectResponse:
    """Retour de Google : vérifie la réponse, ouvre la session, puis renvoie vers le frontend."""
    if google is None:
        return _google_failure(GOOGLE_ERROR_UNAVAILABLE, settings)
    if error is not None:
        logger.info("Connexion Google interrompue : %s", error)
        cancelled = error == GOOGLE_ACCESS_DENIED
        return _google_failure(
            GOOGLE_ERROR_CANCELLED if cancelled else GOOGLE_ERROR_FAILED, settings
        )
    if code is None or state is None or login_cookie is None:
        logger.warning("Retour de Google incomplet (code, state ou cookie manquant)")
        return _google_failure(GOOGLE_ERROR_FAILED, settings)

    try:
        attempt = GoogleLoginAttempt.from_cookie(
            login_cookie, settings.jwt_secret_key.get_secret_value()
        )
    except GoogleAuthError as exc:
        logger.warning("Échec de la connexion Google : %s", exc)
        return _google_failure(GOOGLE_ERROR_FAILED, settings)
    if not attempt.matches_state(state):
        logger.warning("Échec de la connexion Google : state inattendu")
        return _google_failure(GOOGLE_ERROR_FAILED, settings)
    try:
        identity = google.fetch_identity(code, attempt)
    except GoogleAuthError as exc:
        logger.warning("Échec de la connexion Google : %s", exc)
        return _google_failure(GOOGLE_ERROR_FAILED, settings)

    try:
        tokens = service.login_with_google(identity)
    except GoogleEmailNotVerifiedError:
        logger.info("Connexion Google refusée : email non vérifié par Google")
        return _google_failure(GOOGLE_ERROR_EMAIL_NOT_VERIFIED, settings)
    except AccountBannedError as exc:
        return _google_account_banned(exc, settings)

    location = FRONTEND_HOME
    if attempt.next_step == DELETE_ACCOUNT_STEP:
        location = f"{FRONTEND_HOME}?{CONFIRM_PARAM}={DELETE_ACCOUNT_STEP}"
    response = _google_redirect(location, settings)
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return response


@router.get(
    "/google/ban-notice",
    status_code=204,
    responses={403: {"model": ErrorResponse, "description": messages.ACCOUNT_BANNED_DESCRIPTION}},
)
def google_ban_notice(
    service: AuthServiceDep,
    ban_notice_cookie: Annotated[str | None, Cookie(alias=GOOGLE_BAN_NOTICE_COOKIE)] = None,
) -> None:
    """Après un refus de Google : la même réponse 403 qu'une connexion par mot de passe, avec le
    motif et la fin du bannissement. 204 s'il n'y a rien à montrer : pas de cookie ou cookie
    invalide, bannissement levé ou fini."""
    if ban_notice_cookie is None:
        return
    try:
        service.check_ban_notice(ban_notice_cookie)
    except InvalidBanNoticeError:
        logger.info("Cookie du motif d'un bannissement invalide ou expiré")
    except AccountBannedError as exc:
        raise _account_banned(exc) from exc


@router.post("/password/forgot", status_code=204)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    service: AuthServiceDep,
    email_sender: EmailSenderDep,
) -> None:
    """Envoie un lien de réinitialisation si un compte a cette adresse ; répond 204 dans tous les
    cas, après avoir mis l'envoi en tâche de fond : rien ne révèle quelles adresses ont un compte.
    """
    email_to_send = service.request_password_reset(payload.email, payload.language)
    if email_to_send is not None:
        background_tasks.add_task(email_sender.send, email_to_send)


@router.post(
    "/password/reset",
    status_code=204,
    responses={400: {"model": ErrorResponse, "description": messages.INVALID_TOKEN_DESCRIPTION}},
)
def reset_password(payload: ResetPasswordRequest, service: AuthServiceDep) -> None:
    """Choisit un nouveau mot de passe avec le lien reçu ; toutes les sessions sont fermées."""
    try:
        service.reset_password(payload.token, payload.password)
    except InvalidEmailTokenError as exc:
        raise AppHTTPException(
            status_code=400, code=ErrorCode.INVALID_TOKEN, detail=messages.INVALID_TOKEN
        ) from exc
