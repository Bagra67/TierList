from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # backend/.env est aussi lu par le conteneur PostgreSQL (compose.yaml) :
    # les identifiants ne sont définis qu'à un seul endroit.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    # Authentification (docs/authentication.md)
    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    # True en production (HTTPS) ; false en développement local, servi en HTTP
    auth_cookie_secure: bool = True
    # Chemin vu par le navigateur, qui passe par le proxy Vite (/api/auth/... → /auth/...)
    auth_cookie_path: str = "/api/auth"

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
