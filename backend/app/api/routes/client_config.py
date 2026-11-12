from fastapi import APIRouter

from app.api.dependencies import SettingsDep
from app.schemas.client_config import ClientConfigResponse
from app.services.client_config import build_client_config

router = APIRouter(prefix="/client-config", tags=["client-config"])


@router.get("")
def get_client_config(settings: SettingsDep) -> ClientConfigResponse:
    """Configuration publique du navigateur (suivi des erreurs) ; le backend l'écrit aussi dans
    index.html, cette route sert au serveur de développement Vite."""
    return build_client_config(settings)
