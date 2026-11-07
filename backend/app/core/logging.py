import logging.config
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants.logging import APP_LOG_HANDLER, APP_LOGGER

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LoggingSettings(BaseSettings):
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
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(name)s - %(message)s",
                },
            },
            "handlers": {
                APP_LOG_HANDLER: {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                APP_LOGGER: {"handlers": [APP_LOG_HANDLER], "level": level, "propagate": False},
            },
        }
    )
