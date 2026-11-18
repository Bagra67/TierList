from app.core.config import Settings
from app.schemas.client_config import ClientConfigResponse


def build_client_config(settings: Settings) -> ClientConfigResponse:
    return ClientConfigResponse(
        sentry_dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.app_release,
    )
