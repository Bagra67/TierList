from pydantic import BaseModel, Field


class ClientConfigResponse(BaseModel):
    """Public settings read by the frontend at startup.

    The same frontend build serves every environment.
    """

    sentry_dsn: str | None = Field(
        description="Browser Sentry DSN; null when error tracking is disabled."
    )
    environment: str = Field(description="Environment sent to Sentry (staging, production…).")
    release: str = Field(description="Running version, the same as the one of /health.")
