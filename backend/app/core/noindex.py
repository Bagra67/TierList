from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.constants.seo import NOINDEX, X_ROBOTS_TAG_HEADER


class NoindexMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_noindex(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[X_ROBOTS_TAG_HEADER] = NOINDEX
            await send(message)

        await self.app(scope, receive, send_with_noindex)
