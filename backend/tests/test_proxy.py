from ipaddress import ip_network

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.core.proxy import TrustedProxyMiddleware

# Le tunnel joint le pod depuis ce réseau ; 91.197.6.107 est un client qui vise le port directement
PROXY_ADDRESS: str = "10.0.0.7"
DIRECT_CLIENT_ADDRESS: str = "91.197.6.107"


async def whoami(request: Request) -> JSONResponse:
    client_host: str = request.client.host if request.client else ""
    return JSONResponse({"client": client_host, "scheme": request.url.scheme})


async def echo(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_text("hello")
    await websocket.close()


def make_client(peer_address: str) -> TestClient:
    application: Starlette = Starlette(
        routes=[Route("/whoami", whoami), WebSocketRoute("/ws", echo)]
    )
    application.add_middleware(TrustedProxyMiddleware, trusted_networks=[ip_network("10.0.0.0/24")])
    return TestClient(application, client=(peer_address, 50000))


def test_a_direct_connection_is_refused():
    response = make_client(DIRECT_CLIENT_ADDRESS).get("/whoami")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Requests must go through the public address",
        "code": "http_error",
    }


def test_a_direct_connection_cannot_pretend_to_come_from_the_proxy():
    response = make_client(DIRECT_CLIENT_ADDRESS).get(
        "/whoami", headers={"X-Forwarded-For": PROXY_ADDRESS}
    )

    assert response.status_code == 403


def test_a_peer_that_is_not_an_ip_address_is_refused():
    response = make_client("testclient").get("/whoami")

    assert response.status_code == 403


def test_the_proxy_announces_the_real_client_and_scheme():
    response = make_client(PROXY_ADDRESS).get(
        "/whoami", headers={"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"}
    )

    assert response.status_code == 200
    assert response.json() == {"client": "203.0.113.9", "scheme": "https"}


@pytest.mark.parametrize("loopback_address", ["127.0.0.1", "::1"])
def test_the_loopback_is_served_without_trusting_its_headers(loopback_address: str):
    response = make_client(loopback_address).get(
        "/whoami", headers={"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"}
    )

    assert response.status_code == 200
    assert response.json() == {"client": loopback_address, "scheme": "http"}


def test_a_websocket_that_bypasses_the_proxy_is_refused():
    with (
        pytest.raises(WebSocketDisconnect) as disconnect,
        make_client(DIRECT_CLIENT_ADDRESS).websocket_connect("/ws"),
    ):
        pass

    assert disconnect.value.code == 1008


def test_a_websocket_through_the_proxy_is_served():
    with make_client(PROXY_ADDRESS).websocket_connect("/ws") as websocket:
        assert websocket.receive_text() == "hello"
