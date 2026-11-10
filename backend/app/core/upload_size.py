from fastapi.responses import JSONResponse
from starlette import status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.constants import messages
from app.constants.api import CONTENT_LENGTH_HEADER
from app.constants.error_codes import ErrorCode
from app.constants.images import IMAGE_UPLOAD_MULTIPART_OVERHEAD_BYTES, IMAGES_ROUTE_PREFIX
from app.core.errors import ErrorResponse


class ImageUploadSizeMiddleware:
    def __init__(self, app: ASGIApp, max_image_bytes: int) -> None:
        self.app: ASGIApp = app
        self.max_image_bytes: int = max_image_bytes
        self.max_body_bytes: int = max_image_bytes + IMAGE_UPLOAD_MULTIPART_OVERHEAD_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_image_upload(scope):
            await self.app(scope, receive, send)
            return
        if self._declared_too_large(scope):
            await self._refuse(scope, receive, send)
            return
        received_bytes: int = 0
        refused: bool = False

        async def receive_within_limit() -> Message:
            nonlocal received_bytes, refused
            message: Message = await receive()
            if message["type"] != "http.request" or refused:
                return message
            received_bytes += len(message.get("body", b""))
            if received_bytes <= self.max_body_bytes:
                return message
            refused = True
            await self._refuse(scope, receive, send)
            return {"type": "http.disconnect"}

        async def send_unless_refused(message: Message) -> None:
            if not refused:
                await send(message)

        await self.app(scope, receive_within_limit, send_unless_refused)

    async def _refuse(self, scope: Scope, receive: Receive, send: Send) -> None:
        body: ErrorResponse = ErrorResponse(
            detail=messages.IMAGE_TOO_LARGE.format(max_bytes=self.max_image_bytes),
            code=ErrorCode.IMAGE_TOO_LARGE,
            params={"max_bytes": self.max_image_bytes},
        )
        response: JSONResponse = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content=body.model_dump(exclude_none=True),
        )
        await response(scope, receive, send)

    @staticmethod
    def _is_image_upload(scope: Scope) -> bool:
        if scope["type"] != "http" or scope["method"] != "POST":
            return False
        path: str = scope["path"]
        root_path: str = scope.get("root_path", "")
        route_path: str = path.removeprefix(root_path)
        return route_path == IMAGES_ROUTE_PREFIX

    def _declared_too_large(self, scope: Scope) -> bool:
        headers: list[tuple[bytes, bytes]] = scope["headers"]
        for name, value in headers:
            if name.lower() == CONTENT_LENGTH_HEADER:
                try:
                    return int(value) > self.max_body_bytes
                except ValueError:
                    return False
        return False
