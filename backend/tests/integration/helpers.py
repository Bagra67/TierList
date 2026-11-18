import re
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import URL, Connection, event, select
from sqlalchemy.orm import Session

from app.models.account_ban import AccountBan
from app.models.enums import RoomStatus, TemplateModeration, UserRole
from app.models.image import Image
from app.models.room import Room
from app.models.template import Template
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


def confirm_email(db_session: Session, email: str) -> None:
    user: User = db_session.scalars(select(User).where(User.email == email)).one()
    user.email_verified_at = datetime.now(UTC)
    db_session.flush()


def ban_account(db_session: Session, email: str) -> None:
    user: User = db_session.scalars(select(User).where(User.email == email)).one()
    db_session.add(AccountBan(user_id=user.id, actor_name="Nina", reason="Spam"))
    db_session.flush()


def stored_template(db_session: Session, template_id: str) -> Template:
    db_session.expire_all()
    template: Template | None = db_session.get(Template, uuid.UUID(template_id))
    assert template is not None
    return template


def set_hidden(db_session: Session, template_id: str) -> None:
    template: Template = stored_template(db_session, template_id)
    template.moderation = TemplateModeration.HIDDEN
    template.moderation_reason = "Harassment"
    db_session.flush()


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


def create_public_template(
    client: TestClient,
    db_session: Session,
    headers: dict[str, str],
    email: str,
    tile_count: int = 3,
) -> str:
    confirm_email(db_session, email)
    template_id: str = create_template(client, db_session, headers, tile_count)
    response: Response = client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "public"}, headers=headers
    )
    assert response.status_code == 200
    return template_id


def make_private(client: TestClient, template_id: str, owner: dict[str, str]) -> None:
    response: Response = client.put(
        f"/templates/{template_id}/visibility", json={"visibility": "private"}, headers=owner
    )
    assert response.status_code == 200


def delete_template(client: TestClient, template_id: str, owner: dict[str, str]) -> None:
    assert client.delete(f"/templates/{template_id}", headers=owner).status_code == 204


def add_tile_with_image(
    client: TestClient,
    db_session: Session,
    headers: dict[str, str],
    template_id: str,
    text: str | None,
) -> tuple[str, Image]:
    template: Template = stored_template(db_session, template_id)
    image: Image = Image(
        owner_id=template.owner_id,
        storage_key=f"{uuid.uuid4()}.webp",
        width=512,
        height=512,
        size_bytes=4,
        sha256="a" * 64,
    )
    db_session.add(image)
    db_session.flush()
    response: Response = client.post(
        f"/templates/{template_id}/tiles",
        json={"text": text, "image_id": str(image.id)},
        headers=headers,
    )
    assert response.status_code == 201
    tile_id: str = response.json()["tiles"][-1]["id"]
    return tile_id, image


def send_report(
    client: TestClient,
    target_kind: str,
    target_id: str,
    headers: dict[str, str] | None = None,
    reason: str = "spam",
    details: str | None = None,
) -> Response:
    return client.post(
        "/reports",
        json={
            "target_kind": target_kind,
            "target_id": target_id,
            "reason": reason,
            "details": details,
        },
        headers=headers,
    )


def create_room(client: TestClient, headers: dict[str, str], template_id: str) -> JsonObject:
    response: Response = client.post("/rooms", json={"template_id": template_id}, headers=headers)
    assert response.status_code == 201
    return response.json()


def mark_game_in_progress(db_session: Session, code: str) -> None:
    room: Room = db_session.scalars(select(Room).where(Room.code == code)).one()
    room.status = RoomStatus.PLAYING
    db_session.flush()


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


def miss_first_lookup(monkeypatch: pytest.MonkeyPatch, module: object, name: str) -> None:
    lookup: Callable[..., object] = getattr(module, name)
    calls: list[object] = []

    def stale_lookup(*args: object, **kwargs: object) -> object:
        calls.append(args)
        return None if len(calls) == 1 else lookup(*args, **kwargs)

    monkeypatch.setattr(module, name, stale_lookup)
