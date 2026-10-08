"""Réponses d'erreur déclarées dans le schéma OpenAPI, partagées par plusieurs routeurs."""

from typing import Any

from app.constants import messages
from app.core.errors import ErrorResponse

# Toute route protégée par get_current_user peut répondre 401
UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": messages.UNAUTHORIZED_DESCRIPTION}
}
