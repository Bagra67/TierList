import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    get_auth_service,
    get_current_session,
    get_current_user,
    get_google_oauth_client,
)
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse
from app.models.user import User
from app.schemas.auth import (
    DeleteAccountRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    AuthenticatedSession,
    AuthService,
    EmailAlreadyRegisteredError,
    GoogleEmailNotVerifiedError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    IssuedTokens,
    ReauthenticationRequiredError,
)
from app.services.google_oauth import GoogleAuthError, GoogleLoginAttempt, GoogleOAuthClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_COOKIE = "refresh_token"

UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Non authentifié"}
}

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RefreshTokenCookie = Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)]
GoogleClientDep = Annotated[GoogleOAuthClient | None, Depends(get_google_oauth_client)]

GOOGLE_LOGIN_COOKIE = "google_login"
# Seule étape qu'on peut reprendre après Google : une liste fermée évite toute redirection ouverte
GoogleNextStep = Literal["delete-account"]
# Pages du frontend vers lesquelles le retour de Google redirige (même origine, via le proxy)
FRONTEND_HOME = "/"
FRONTEND_LOGIN = "/login"


def _set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    # HttpOnly : illisible par JavaScript (XSS). SameSite=Strict + chemin limité à /api/auth :
    # le navigateur ne l'envoie qu'aux routes d'authentification, et jamais depuis un autre site.
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
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


def _session_expired(settings: Settings) -> HTTPException:
    # Les en-têtes de la réponse injectée sont perdus quand une exception est levée :
    # l'effacement du cookie invalide passe par les en-têtes de l'HTTPException.
    cleared = Response()
    _clear_refresh_cookie(cleared, settings)
    return HTTPException(
        status_code=401,
        detail="Session expirée, veuillez vous reconnecter",
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
    responses={409: {"model": ErrorResponse, "description": "Email déjà utilisé"}},
)
def register(
    payload: RegisterRequest, response: Response, service: AuthServiceDep, settings: SettingsDep
) -> TokenResponse:
    try:
        tokens = service.register(payload.email, payload.password, payload.display_name)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé") from exc
    return _token_response(response, tokens, settings)


@router.post("/login", responses=UNAUTHORIZED_RESPONSE)
def login(
    payload: LoginRequest, response: Response, service: AuthServiceDep, settings: SettingsDep
) -> TokenResponse:
    try:
        tokens = service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        # Même message que l'email existe ou non : ne révèle pas quels comptes existent
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect") from exc
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
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)


@router.delete(
    "/me",
    status_code=204,
    responses={
        **UNAUTHORIZED_RESPONSE,
        # 403 et non 401 : l'utilisateur est bien authentifié, seule la confirmation est fausse
        403: {
            "model": ErrorResponse,
            "description": "Mot de passe incorrect, ou connexion Google trop ancienne",
        },
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
        raise HTTPException(status_code=403, detail="Mot de passe incorrect") from exc
    except ReauthenticationRequiredError as exc:
        raise HTTPException(
            status_code=403,
            detail="Reconnectez-vous avec Google pour confirmer la suppression",
        ) from exc
    _clear_refresh_cookie(response, settings)


def _google_cookie_path(settings: Settings) -> str:
    return f"{settings.auth_cookie_path}/google"


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
    return _google_redirect(f"{FRONTEND_LOGIN}?error={error_code}", settings)


@router.get("/google/login", status_code=302, response_class=RedirectResponse)
def google_login(
    settings: SettingsDep,
    google: GoogleClientDep,
    next_step: Annotated[GoogleNextStep | None, Query(alias="next")] = None,
) -> RedirectResponse:
    """Envoie le navigateur sur la page de connexion de Google."""
    if google is None:
        return _google_failure("google_unavailable", settings)
    attempt = GoogleLoginAttempt.start(next_step)
    response = RedirectResponse(google.authorization_url(attempt), status_code=302)
    # SameSite=Lax et non Strict : le retour depuis Google est une navigation venant d'un autre
    # site, pour laquelle le navigateur n'enverrait pas un cookie Strict.
    response.set_cookie(
        GOOGLE_LOGIN_COOKIE,
        attempt.to_cookie(settings.jwt_secret_key.get_secret_value()),
        max_age=10 * 60,
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
        return _google_failure("google_unavailable", settings)
    if error is not None:
        # access_denied : l'utilisateur a refusé ou fermé la page de Google
        logger.info("Connexion Google interrompue : %s", error)
        code_name = "google_cancelled" if error == "access_denied" else "google_failed"
        return _google_failure(code_name, settings)
    if code is None or state is None or login_cookie is None:
        logger.warning("Retour de Google incomplet (code, state ou cookie manquant)")
        return _google_failure("google_failed", settings)

    try:
        attempt = GoogleLoginAttempt.from_cookie(
            login_cookie, settings.jwt_secret_key.get_secret_value()
        )
    except GoogleAuthError as exc:
        logger.warning("Échec de la connexion Google : %s", exc)
        return _google_failure("google_failed", settings)
    if not attempt.matches_state(state):
        # Retour qui ne correspond pas à la tentative de ce navigateur : possible CSRF
        logger.warning("Échec de la connexion Google : state inattendu")
        return _google_failure("google_failed", settings)
    try:
        identity = google.fetch_identity(code, attempt)
    except GoogleAuthError as exc:
        logger.warning("Échec de la connexion Google : %s", exc)
        return _google_failure("google_failed", settings)

    try:
        tokens = service.login_with_google(identity)
    except GoogleEmailNotVerifiedError:
        logger.info("Connexion Google refusée : email non vérifié par Google")
        return _google_failure("google_email_not_verified", settings)

    location = FRONTEND_HOME
    if attempt.next_step == "delete-account":
        location = f"{FRONTEND_HOME}?confirm=delete-account"
    response = _google_redirect(location, settings)
    _set_refresh_cookie(response, tokens.refresh_token, settings)
    return response
