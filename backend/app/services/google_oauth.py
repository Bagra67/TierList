"""Connexion avec Google (OpenID Connect, flux « authorization code » avec PKCE).

Références : https://developers.google.com/identity/openid-connect/openid-connect
"""

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

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
HTTP_TIMEOUT_SECONDS = 10

# Durée laissée à l'utilisateur pour choisir son compte sur la page de Google
LOGIN_ATTEMPT_TTL = timedelta(minutes=10)
LOGIN_ATTEMPT_TOKEN_TYPE = "google_login"
LOGIN_ATTEMPT_ALGORITHM = "HS256"


class GoogleAuthError(Exception):
    """Réponse de Google absente, invalide ou falsifiée ; le message ne contient aucun secret."""


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
            state=secrets.token_urlsafe(32),
            nonce=secrets.token_urlsafe(32),
            code_verifier=secrets.token_urlsafe(64),
            next_step=next_step,
        )

    @property
    def code_challenge(self) -> str:
        digest = hashlib.sha256(self.code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    def to_cookie(self, secret_key: str) -> str:
        # Signé (JWT HS256) : le navigateur le garde, mais ne peut pas le modifier
        now = datetime.now(UTC)
        claims = {
            "type": LOGIN_ATTEMPT_TOKEN_TYPE,
            "state": self.state,
            "nonce": self.nonce,
            "code_verifier": self.code_verifier,
            "next": self.next_step,
            "iat": now,
            "exp": now + LOGIN_ATTEMPT_TTL,
        }
        return jwt.encode(claims, secret_key, algorithm=LOGIN_ATTEMPT_ALGORITHM)

    @classmethod
    def from_cookie(cls, value: str, secret_key: str) -> "GoogleLoginAttempt":
        try:
            claims = jwt.decode(
                value,
                secret_key,
                algorithms=[LOGIN_ATTEMPT_ALGORITHM],
                options={"require": ["type", "state", "nonce", "code_verifier", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise GoogleAuthError("Tentative de connexion invalide ou expirée") from exc
        if claims["type"] != LOGIN_ATTEMPT_TOKEN_TYPE:
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
def _google_jwk_client() -> jwt.PyJWKClient:
    # Partagé entre les requêtes : garde en cache les clés publiques de Google
    return jwt.PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True, timeout=HTTP_TIMEOUT_SECONDS)


class GoogleOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        *,
        transport: httpx.BaseTransport | None = None,
        jwk_client: jwt.PyJWKClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        # Remplaçables dans les tests : aucun appel réseau vers Google
        self._transport = transport
        self._jwk_client = jwk_client

    def authorization_url(self, attempt: GoogleLoginAttempt) -> str:
        query = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": attempt.state,
            "nonce": attempt.nonce,
            "code_challenge": attempt.code_challenge,
            "code_challenge_method": "S256",
            # Laisse choisir le compte quand plusieurs sont ouverts dans le navigateur
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(query)}"

    def fetch_identity(self, code: str, attempt: GoogleLoginAttempt) -> GoogleIdentity:
        id_token = self._exchange_code(code, attempt.code_verifier)
        return self._verify_id_token(id_token, attempt.nonce)

    def _exchange_code(self, code: str, code_verifier: str) -> str:
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, transport=self._transport) as client:
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
        jwk_client = self._jwk_client or _google_jwk_client()
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
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
