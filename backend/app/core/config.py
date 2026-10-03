from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.constants.auth import JWT_SECRET_KEY_MIN_LENGTH, PASSWORD_MAX_LENGTH


class Settings(BaseSettings):
    # backend/.env est aussi lu par le conteneur PostgreSQL (compose.yaml) :
    # les identifiants ne sont définis qu'à un seul endroit.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    # Sans délai, une connexion vers une base arrêtée peut bloquer la requête très longtemps
    database_connect_timeout_seconds: int = Field(default=3, gt=0)

    # Authentification (docs/authentication.md)
    jwt_secret_key: SecretStr = Field(min_length=JWT_SECRET_KEY_MIN_LENGTH)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    password_min_length: int = Field(default=8, gt=0, le=PASSWORD_MAX_LENGTH)
    # Compte sans mot de passe (Google) : âge maximal de la connexion pour supprimer le compte
    recent_authentication_max_age_minutes: int = Field(default=5, gt=0)
    # True en production (HTTPS) ; false en développement local, servi en HTTP
    auth_cookie_secure: bool = True
    # Chemin vu par le navigateur, qui passe par le proxy Vite (/api/auth/... → /auth/...)
    auth_cookie_path: str = "/api/auth"

    # Connexion avec Google (client OAuth « Application Web » de la Google Cloud Console).
    # Sans identifiants, le bouton Google renvoie vers /login avec une erreur explicite.
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    # Doit figurer à l'identique dans les « URI de redirection autorisés » du client Google
    google_redirect_uri: str = "http://localhost:5173/api/auth/google/callback"
    # Temps laissé à l'utilisateur sur la page de Google avant que la tentative expire
    google_login_attempt_ttl_minutes: int = Field(default=10, gt=0)
    # Délai des appels vers Google (échange du code, clés publiques)
    google_http_timeout_seconds: int = Field(default=10, gt=0)

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    # Les champs obligatoires sont lus depuis l'environnement / .env par pydantic-settings,
    # ce que Pyright ne peut pas savoir statiquement.
    return Settings()  # pyright: ignore[reportCallIssue]
