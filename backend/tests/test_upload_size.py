import asyncio
import json

import pytest
from starlette.types import Message, Receive, Scope, Send

from app.constants.images import IMAGE_UPLOAD_MULTIPART_OVERHEAD_BYTES
from app.core.config import get_settings
from app.core.upload_size import ImageUploadSizeMiddleware
from app.main import api_app

MAX_IMAGE_BYTES = 1000
MAX_BODY_BYTES = MAX_IMAGE_BYTES + IMAGE_UPLOAD_MULTIPART_OVERHEAD_BYTES


class ReachedApp:
    def __init__(self) -> None:
        self.reached: bool = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.reached = True


def request_scope(method: str, path: str, content_length: str | None) -> Scope:
    headers: list[tuple[bytes, bytes]] = []
    if content_length is not None:
        headers.append((b"content-length", content_length.encode()))
    return {"type": "http", "method": method, "path": path, "root_path": "/api", "headers": headers}


def call(scope: Scope) -> tuple[ReachedApp, list[Message]]:
    app: ReachedApp = ReachedApp()
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b""}

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(ImageUploadSizeMiddleware(app, MAX_IMAGE_BYTES)(scope, receive, send))
    return app, sent


def test_an_image_upload_declared_too_large_is_refused_before_its_body_is_read():
    app, sent = call(request_scope("POST", "/api/images", str(MAX_BODY_BYTES + 1)))

    assert app.reached is False
    assert sent[0]["status"] == 413
    body: dict[str, object] = json.loads(sent[1]["body"])
    assert body["code"] == "image_too_large"
    assert body["params"] == {"max_bytes": MAX_IMAGE_BYTES}


@pytest.mark.parametrize(
    ("method", "path", "content_length"),
    [
        ("POST", "/api/images", str(MAX_BODY_BYTES)),
        ("POST", "/api/images", None),
        ("POST", "/api/images", "not a number"),
        ("POST", "/api/templates", str(MAX_BODY_BYTES + 1)),
        ("GET", "/api/images", str(MAX_BODY_BYTES + 1)),
    ],
)
def test_other_requests_reach_the_application(method: str, path: str, content_length: str | None):
    app, sent = call(request_scope(method, path, content_length))

    assert app.reached is True
    assert sent == []


class BodyReadingApp:
    def __init__(self) -> None:
        self.received: list[Message] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message: Message = await receive()
            self.received.append(message)
            if message["type"] == "http.disconnect" or not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"stored"})


def stream(chunks: list[bytes]) -> tuple[BodyReadingApp, list[Message]]:
    app: BodyReadingApp = BodyReadingApp()
    sent: list[Message] = []
    remaining: list[Message] = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> Message:
        return remaining.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(
        ImageUploadSizeMiddleware(app, MAX_IMAGE_BYTES)(
            request_scope("POST", "/api/images", None), receive, send
        )
    )
    return app, sent


def test_an_image_upload_sent_without_length_is_stopped_once_over_the_limit():
    chunk: bytes = b"x" * (MAX_BODY_BYTES // 2 + 1)

    app, sent = stream([chunk, chunk, chunk])

    assert [message["type"] for message in app.received] == ["http.request", "http.disconnect"]
    assert [message.get("status") for message in sent if "status" in message] == [413]
    assert all(message.get("body") != b"stored" for message in sent)


def test_an_image_upload_sent_without_length_within_the_limit_reaches_the_application():
    app, sent = stream([b"x" * 100, b"x" * 100])

    assert len(app.received) == 2
    assert sent[0]["status"] == 200


def test_the_api_checks_the_size_of_image_uploads():
    registered: list[object] = [
        middleware.kwargs
        for middleware in api_app.user_middleware
        if middleware.cls is ImageUploadSizeMiddleware
    ]

    assert registered == [{"max_image_bytes": get_settings().image_upload_max_bytes}]
