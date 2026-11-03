import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from alembic.config import Config
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import URL, Connection, event, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.tile import Tile
from app.models.user import User
from app.services.email import Email

BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)


def alembic_config(database_url: URL) -> Config:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    url = database_url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def link_token(email: Email) -> str:
    match = re.search(r"https?://\S+", email.text)
    assert match is not None, "aucun lien dans l'email"
    return parse_qs(urlparse(match.group()).query)["token"][0]


PASSWORD = "correct horse battery staple"

JsonObject = dict[str, Any]


def register(client: TestClient, email: str) -> dict[str, str]:
    response: Response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_super_admin(client: TestClient, db_session: Session, email: str) -> dict[str, str]:
    headers: dict[str, str] = register(client, email)
    user: User = db_session.scalars(select(User).where(User.email == email)).one()
    user.role = UserRole.SUPER_ADMIN
    db_session.flush()
    return headers


def create_template(
    client: TestClient, db_session: Session, headers: dict[str, str], tile_count: int = 3
) -> str:
    response: Response = client.post("/templates", json={"name": "Food"}, headers=headers)
    assert response.status_code == 201
    template_id: str = response.json()["id"]
    for position in range(tile_count):
        db_session.add(
            Tile(template_id=uuid.UUID(template_id), text=f"Tile {position}", position=position)
        )
    db_session.flush()
    return template_id


def create_room(client: TestClient, headers: dict[str, str], template_id: str) -> JsonObject:
    response: Response = client.post("/rooms", json={"template_id": template_id}, headers=headers)
    assert response.status_code == 201
    return response.json()


def start_game(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/game", headers=headers)
    assert response.status_code == 201
    return response.json()


def next_item(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/game/next", headers=headers)
    assert response.status_code == 200
    return response.json()


def place(
    client: TestClient,
    code: str,
    tile_id: str,
    tier_id: str,
    position: int,
    headers: dict[str, str] | None = None,
) -> Response:
    return client.put(
        f"/rooms/{code}/game/placements/{tile_id}",
        json={"tier_id": tier_id, "position": position},
        headers=headers,
    )


def board(room: JsonObject) -> list[tuple[str, str | None, int]]:
    tier_names: dict[str, str] = {tier["id"]: tier["name"] for tier in room["game"]["tiers"]}
    return [
        (tier_names[placement["tier_id"]], placement["item"]["text"], placement["position"])
        for placement in room["game"]["own_placements"]
    ]


def place_current_in_first_tier(
    client: TestClient, room: JsonObject, headers: dict[str, str] | None = None
) -> None:
    game: JsonObject = room["game"]
    response: Response = place(
        client, room["code"], game["current_item"]["id"], game["tiers"][0]["id"], 0, headers
    )
    assert response.status_code == 200


def play_and_close(client: TestClient, code: str, admin: dict[str, str]) -> JsonObject:
    room: JsonObject = client.get(f"/rooms/{code}", headers=admin).json()
    while room["game"]["status"] == "in_round":
        room = next_item(client, code, admin)
    response: Response = client.post(f"/rooms/{code}/game/end", headers=admin)
    assert response.status_code == 200
    return response.json()


@contextmanager
def counted_queries(db_session: Session) -> Iterator[list[str]]:
    statements: list[str] = []
    connection: Connection = db_session.connection()

    def record(*args: Any) -> None:
        statements.append(args[2])

    event.listen(connection, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", record)
