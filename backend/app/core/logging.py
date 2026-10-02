import logging.config
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Seuls les loggers de l'application (« app » et ses enfants : app.main, app.db…) sont
# configurés ici ; uvicorn garde sa propre configuration (option --log-level).
APP_LOGGER = "app"


class LoggingSettings(BaseSettings):
    # Séparé de Settings : l'application doit pouvoir journaliser même si la
    # configuration PostgreSQL est absente.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: LogLevel = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


@lru_cache
def get_logging_settings() -> LoggingSettings:
    return LoggingSettings()


def configure_logging(level: LogLevel) -> None:
    """Envoie les logs de l'application sur stderr, au même format que ceux d'uvicorn."""
    logging.config.dictConfig(
        {
            "version": 1,
            # Ne pas désactiver les loggers déjà configurés (uvicorn, SQLAlchemy…).
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(name)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                APP_LOGGER: {"handlers": ["default"], "level": level, "propagate": False},
            },
        }
    )
