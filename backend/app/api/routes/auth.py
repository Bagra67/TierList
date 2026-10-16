import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_current_user,
    get_email_sender,
    get_google_oauth_client,
)
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.auth import (
    CONFIRM_PARAM,
    DELETE_ACCOUNT_STEP,
    FRONTEND_HOME,
    FRONTEND_LOGIN,
    GOOGLE_ACCESS_DENIED,
    GOOGLE_COOKIE_SUBPATH,
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
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse
from app.exceptions.auth import (
    EmailAlreadyRegisteredError,
    GoogleEmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidEmailTokenError,
    InvalidRefreshTokenError,
    ReauthenticationRequiredError,
)
from app.exceptions.google import GoogleAuthError
from app.exceptions.http import AppHTTPException
from app.models.user import User
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
from app.services.auth import AuthenticatedSession, AuthService, IssuedTokens
from app.services.email import EmailSender
from app.services.google_oauth import GoogleLoginAttempt, GoogleOAuthClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RefreshTokenCookie = Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)]
GoogleClientDep = Annotated[GoogleOAuthClient | None, Depends(get_google_oauth_client)]
EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    # HttpOnly : illisible par JavaScript (XSS). SameSite=Strict + chemin limité à /api/auth :
    # le navigateur ne l'envoie qu'aux routes d'authentification, et jamais depuis un autre site.
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


def _session_expired(settings: Settings) -> AppHTTPException:
    # Les en-têtes de la réponse injectée sont perdus quand une exception est levée :
    # l'effacement du cookie invalide passe par les en-têtes de l'exception.
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
    # Après la réponse : l'inscription n'attend pas le serveur SMTP
    background_tasks.add_task(email_sender.send, registration.verification_email)
    return _token_response(response, registration.tokens, settings)


@router.post("/login", responses=UNAUTHORIZED_RESPONSE)
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
        # 403 et non 401 : l'utilisateur est bien authentifié, seule la confirmation est fausse
        403: {"model": ErrorResponse, "description": messages.DELETE_ACCOUNT_FORBIDDEN_DESCRIPTION},
    },
)
def delete_me(
    payload: DeleteAccountRequest,
    response: Response,
    session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    service: AuthServiceDep,
    settings: SettingsDep,
) -> None:
    try:
        service.delete_account(session, payload.password)
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
    # La tentative de connexion ne sert qu'une fois : son cookie est effacé dans tous les cas
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
    # SameSite=Lax et non Strict : le retour depuis Google est une navigation venant d'un autre
    # site, pour laquelle le navigateur n'enverrait pas un cookie Strict.
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
        # access_denied : l'utilisateur a refusé ou fermé la page de Google
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
        # Retour qui ne correspond pas à la tentative de ce navigateur : possible CSRF
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

    location = FRONTEND_HOME
    if attempt.next_step == DELETE_ACCOUNT_STEP:
        location = f"{FRONTEND_HOME}?{CONFIRM_PARAM}={DELETE_ACCOUNT_STEP}"
    response = _google_redirect(location, settings)
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return response


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
