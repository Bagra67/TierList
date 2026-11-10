from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.schemas.client_config import ClientConfigResponse

router = APIRouter(prefix="/client-config", tags=["client-config"])


@router.get("")
def get_client_config(settings: SettingsDep) -> ClientConfigResponse:
    return ClientConfigResponse(
        sentry_dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.app_release,
    )
