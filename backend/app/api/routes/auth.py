from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from app.api.dependencies import get_auth_service, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    IssuedTokens,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_COOKIE = "refresh_token"

UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Non authentifié"}
}

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RefreshTokenCookie = Annotated[str | None, Cookie(alias=REFRESH_TOKEN_COOKIE)]


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
