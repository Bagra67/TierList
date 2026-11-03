from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, IPvAnyNetwork, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL

from app.constants.api import API_PREFIX
from app.constants.auth import JWT_SECRET_KEY_MIN_LENGTH, PASSWORD_MAX_LENGTH
from app.constants.rooms import (
    COOLDOWN_SECONDS_MAX,
    COOLDOWN_SECONDS_MIN,
    GUEST_LINK_MAX_TTL_DAYS,
    TIMER_SECONDS_MAX,
    TIMER_SECONDS_MIN,
)

BACKEND_DIR: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    database_connect_timeout_seconds: int = Field(default=3, gt=0)

    jwt_secret_key: SecretStr = Field(min_length=JWT_SECRET_KEY_MIN_LENGTH)
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    password_min_length: int = Field(default=8, gt=0, le=PASSWORD_MAX_LENGTH)
    recent_authentication_max_age_minutes: int = Field(default=5, gt=0)
    email_verification_ttl_hours: int = Field(default=24, gt=0)
    password_reset_ttl_minutes: int = Field(default=30, gt=0)
    email_cooldown_seconds: int = Field(default=60, ge=0)
    auth_cookie_secure: bool = True
    auth_cookie_path: str = f"{API_PREFIX}/auth"

    deleted_template_retention_days: int = Field(default=30, gt=0)

    moderation_log_retention_days: int = Field(default=3 * 365, gt=0)

    room_default_timer_seconds: int = Field(default=30, ge=TIMER_SECONDS_MIN, le=TIMER_SECONDS_MAX)
    room_default_cooldown_seconds: int = Field(
        default=60, ge=COOLDOWN_SECONDS_MIN, le=COOLDOWN_SECONDS_MAX
    )
    guest_link_ttl_days: int = Field(default=30, gt=0, le=GUEST_LINK_MAX_TTL_DAYS)
    room_cookie_path: str = f"{API_PREFIX}/rooms"
    room_heartbeat_interval_seconds: float = Field(default=10, gt=0)
    room_heartbeat_timeout_seconds: float = Field(default=5, gt=0)
    room_presence_grace_seconds: float = Field(default=3, ge=0)
    room_auth_timeout_seconds: float = Field(default=5, gt=0)
    room_inactivity_hours: float = Field(default=24, gt=0)
    room_inactivity_sweep_minutes: float = Field(default=15, gt=0)

    image_upload_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    image_max_source_pixels: int = Field(default=40_000_000, gt=0)
    image_uploads_per_hour_max: int = Field(default=120, gt=0)
    unused_image_retention_days: int = Field(default=7, gt=0)
    image_s3_endpoint_url: str | None = None
    image_s3_bucket: str = "tierlist-images"
    image_s3_region: str = "us-east-1"
    image_s3_access_key_id: str | None = None
    image_s3_secret_access_key: SecretStr | None = None
    image_s3_timeout_seconds: int = Field(default=10, gt=0)
    image_public_base_url: str = "http://127.0.0.1:8333/tierlist-images"

    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str = f"http://localhost:5173{API_PREFIX}/auth/google/callback"
    google_login_attempt_ttl_minutes: int = Field(default=10, gt=0)
    google_http_timeout_seconds: int = Field(default=10, gt=0)

    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = Field(default=10, gt=0)
    email_from: str = "TierList <no-reply@localhost>"
    frontend_base_url: str = "http://localhost:5173"

    frontend_dist: Path = BACKEND_DIR.parent / "frontend_dist"
    app_release: str = "dev"
    maintenance_enabled: bool = True
    maintenance_hour_utc: int = Field(default=3, ge=0, le=23)
    trusted_proxy_ips: Annotated[list[IPvAnyNetwork], NoDecode] = []

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def _split_trusted_proxy_ips(cls, value: object) -> object:
        if isinstance(value, str):
            return [address.strip() for address in value.split(",") if address.strip()]
        return value

    @property
    def app_origin(self) -> str:
        parts = urlsplit(self.frontend_base_url)
        return f"{parts.scheme}://{parts.netloc}"

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
    return Settings()  # pyright: ignore[reportCallIssue]
