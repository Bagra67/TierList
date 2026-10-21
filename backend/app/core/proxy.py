"""Accès par le proxy seulement (docs/technical/deployment.md, §2.2)."""

from collections.abc import Sequence
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import cast

from fastapi.responses import JSONResponse
from pydantic import IPvAnyNetwork
from starlette import status
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketClose
from uvicorn._types import ASGI3Application
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse


class TrustedProxyMiddleware:
    """Le port du pod est public : seules les connexions du proxy (Cloudflare Tunnel) et de la
    boucle locale (attente de /api/health par start.sh) sont servies, toute autre est refusée.
    Seul le proxy peut aussi annoncer le vrai client et le schéma (X-Forwarded-For,
    X-Forwarded-Proto).

    Remplace --proxy-headers d'uvicorn (lancé avec --no-proxy-headers) : uvicorn réécrirait le
    client avant l'application, l'adresse de la connexion ne serait plus visible ici. Middleware
    ASGI pur : pas de tâche à part par requête, contrairement à BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp, trusted_networks: Sequence[IPvAnyNetwork]) -> None:
        self.trusted_networks: tuple[IPvAnyNetwork, ...] = tuple(trusted_networks)
        trusted_hosts: list[str] = [str(network) for network in self.trusted_networks]
        # uvicorn et Starlette typent l'ASGI chacun à leur façon, pour la même interface
        proxy_headers: object = ProxyHeadersMiddleware(
            cast(ASGI3Application, app), trusted_hosts=trusted_hosts
        )
        self.app: ASGIApp = cast(ASGIApp, proxy_headers)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not self._from_trusted_peer(scope):
            body: ErrorResponse = ErrorResponse(
                detail=messages.DIRECT_ACCESS_FORBIDDEN, code=ErrorCode.HTTP_ERROR
            )
            response: JSONResponse = JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN, content=body.model_dump(exclude_none=True)
            )
            await response(scope, receive, send)
            return
        if scope["type"] == "websocket" and not self._from_trusted_peer(scope):
            # Fermé avant d'être accepté : uvicorn répond 403 à la poignée de main
            await WebSocketClose(code=status.WS_1008_POLICY_VIOLATION)(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _from_trusted_peer(self, scope: Scope) -> bool:
        """Adresse de la connexion TCP, pas celle d'un en-tête que le client peut écrire."""
        client: tuple[str, int] | None = scope.get("client")
        if client is None:
            return False
        try:
            peer: IPv4Address | IPv6Address = ip_address(client[0])
        except ValueError:
            return False
        return peer.is_loopback or any(peer in network for network in self.trusted_networks)
