"""Connexion avec Google (OpenID Connect, flux « authorization code » avec PKCE)."""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.constants.auth import (
    GOOGLE_LOGIN_TOKEN_TYPE,
    GOOGLE_NONCE_BYTES,
    GOOGLE_STATE_BYTES,
    JWT_ALGORITHM,
    PKCE_VERIFIER_BYTES,
)
from app.constants.google import (
    GOOGLE_AUTHORIZATION_URL,
    GOOGLE_ID_TOKEN_ALGORITHM,
    GOOGLE_ISSUERS,
    GOOGLE_JWKS_URL,
    GOOGLE_PROMPT,
    GOOGLE_SCOPES,
    GOOGLE_TOKEN_URL,
    PKCE_CHALLENGE_METHOD,
)
from app.exceptions.google import GoogleAuthError


@dataclass(frozen=True)
class GoogleIdentity:
    # Identifiant stable du compte Google (claim « sub »)
    subject: str
    email: str
    email_verified: bool
    name: str | None


@dataclass(frozen=True)
class GoogleLoginAttempt:
    """Secrets d'une tentative de connexion, conservés entre le départ vers Google et le retour.

    - state : protège le retour contre le CSRF (il doit revenir à l'identique) ;
    - nonce : lie l'id_token reçu à cette tentative (contre le rejeu) ;
    - code_verifier : PKCE, rend inutilisable un code d'autorisation intercepté.
    """

    state: str
    nonce: str
    code_verifier: str
    # Étape à reprendre après la connexion (ex. « delete-account »), ou None
    next_step: str | None

    @classmethod
    def start(cls, next_step: str | None) -> "GoogleLoginAttempt":
        return cls(
            state=secrets.token_urlsafe(GOOGLE_STATE_BYTES),
            nonce=secrets.token_urlsafe(GOOGLE_NONCE_BYTES),
            code_verifier=secrets.token_urlsafe(PKCE_VERIFIER_BYTES),
            next_step=next_step,
        )

    @property
    def code_challenge(self) -> str:
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def to_cookie(self, secret_key: str, ttl: timedelta) -> str:
        # Signé (JWT HS256) : le navigateur le garde, mais ne peut pas le modifier
        now = datetime.now(UTC)
        claims = {
            "type": GOOGLE_LOGIN_TOKEN_TYPE,
            "state": self.state,
            "nonce": self.nonce,
            "code_verifier": self.code_verifier,
            "next": self.next_step,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(claims, secret_key, algorithm=JWT_ALGORITHM)

    @classmethod
    def from_cookie(cls, value: str, secret_key: str) -> "GoogleLoginAttempt":
        try:
            claims = jwt.decode(
                value,
                secret_key,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["type", "state", "nonce", "code_verifier", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise GoogleAuthError("Tentative de connexion invalide ou expirée") from exc
        if claims["type"] != GOOGLE_LOGIN_TOKEN_TYPE:
            raise GoogleAuthError("Tentative de connexion invalide")
        return cls(
            state=claims["state"],
            nonce=claims["nonce"],
            code_verifier=claims["code_verifier"],
            next_step=claims.get("next"),
        )

    def matches_state(self, state: str) -> bool:
        return secrets.compare_digest(self.state, state)


@lru_cache
def _google_jwk_client(timeout_seconds: int) -> jwt.PyJWKClient:
    # Partagé entre les requêtes : garde en cache les clés publiques de Google
    return jwt.PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True, timeout=timeout_seconds)


class GoogleOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        *,
        http_timeout_seconds: int,
        transport: httpx.BaseTransport | None = None,
        jwk_client: jwt.PyJWKClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http_timeout_seconds = http_timeout_seconds
        # Remplaçables dans les tests : aucun appel réseau vers Google
        self._transport = transport
        self._jwk_client = jwk_client

    def authorization_url(self, attempt: GoogleLoginAttempt) -> str:
        query = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "state": attempt.state,
            "nonce": attempt.nonce,
            "code_challenge": attempt.code_challenge,
            "code_challenge_method": PKCE_CHALLENGE_METHOD,
            "prompt": GOOGLE_PROMPT,
        }
        return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(query)}"

    def fetch_identity(self, code: str, attempt: GoogleLoginAttempt) -> GoogleIdentity:
        id_token = self._exchange_code(code, attempt.code_verifier)
        return self._verify_id_token(id_token, attempt.nonce)

    def _exchange_code(self, code: str, code_verifier: str) -> str:
        try:
            with httpx.Client(
                timeout=self._http_timeout_seconds, transport=self._transport
            ) as client:
                response = client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": self._redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": code_verifier,
                    },
                )
            response.raise_for_status()
            body: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GoogleAuthError(f"Échange du code refusé par Google : {exc}") from exc
        id_token = body.get("id_token") if isinstance(body, dict) else None
        if not isinstance(id_token, str):
            raise GoogleAuthError("Réponse de Google sans id_token")
        return id_token

    def _verify_id_token(self, id_token: str, nonce: str) -> GoogleIdentity:
        jwk_client = self._jwk_client or _google_jwk_client(self._http_timeout_seconds)
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[GOOGLE_ID_TOKEN_ALGORITHM],
                audience=self._client_id,
                issuer=GOOGLE_ISSUERS,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "nonce"]},
            )
        except jwt.PyJWTError as exc:
            raise GoogleAuthError(f"id_token invalide : {exc}") from exc
        if not secrets.compare_digest(str(claims["nonce"]), nonce):
            raise GoogleAuthError("id_token émis pour une autre tentative de connexion")
        email = claims.get("email")
        if not isinstance(email, str):
            raise GoogleAuthError("id_token sans email")
        name = claims.get("name")
        return GoogleIdentity(
            subject=str(claims["sub"]),
            email=email,
            email_verified=claims.get("email_verified") is True,
            name=name if isinstance(name, str) else None,
        )
