"""Réponses d'erreur déclarées dans le schéma OpenAPI, partagées par plusieurs routeurs."""

from typing import Any

from app.constants import messages
from app.core.errors import ErrorResponse

# Toute route protégée par get_current_user peut répondre 401
UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": messages.UNAUTHORIZED_DESCRIPTION}
}

# Toute route protégée par get_current_super_admin (les routes de modération) : 401, puis 403
SUPER_ADMIN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    403: {"model": ErrorResponse, "description": messages.SUPER_ADMIN_REQUIRED_DESCRIPTION},
}
