from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.schemas.client_config import ClientConfigResponse
from app.services.client_config import build_client_config

router = APIRouter(prefix="/client-config", tags=["client-config"])


@router.get("")
def get_client_config(settings: SettingsDep) -> ClientConfigResponse:
    """Public browser configuration (error tracking); the backend also writes it into index.html,
    this route serves the Vite development server."""
    return build_client_config(settings)
