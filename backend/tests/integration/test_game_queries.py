"""Nombre de requêtes SQL d'une partie et de ses résultats : constant, quel que soit le nombre
d'items (pas de N+1)."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Connection, event
from sqlalchemy.orm import Session

from tests.integration.helpers import (
    JsonObject,
    create_room,
    create_template,
    next_item,
    place,
    play_and_close,
    register,
    start_game,
)

pytestmark = pytest.mark.integration


@contextmanager
def counted_queries(db_session: Session) -> Iterator[list[str]]:
    """Les requêtes SQL envoyées par la session du test pendant le bloc."""
    statements: list[str] = []
    connection: Connection = db_session.connection()

    def record(*args: Any) -> None:
        statements.append(args[2])

    event.listen(connection, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", record)


def played_room(client: TestClient, db_session: Session, email: str, tile_count: int) -> JsonObject:
    """Une salle dont la partie a eu tous ses tours placés : le plateau tient tile_count items."""
    headers: dict[str, str] = register(client, email)
    room: JsonObject = create_room(
        client, headers, create_template(client, db_session, headers, tile_count=tile_count)
    )
    current: JsonObject = start_game(client, room["code"], headers)
    for _ in range(tile_count - 1):
        game: JsonObject = current["game"]
        placed: Response = place(
            client, room["code"], game["current_item"]["id"], game["tiers"][0]["id"], 0, headers
        )
        assert placed.status_code == 200
        current = next_item(client, room["code"], headers)
    current["headers"] = headers
    return current


def send(client: TestClient, room: JsonObject, action: str) -> Response:
    """Relit la salle, replace l'item en cours en tête du premier tier, ou lit les résultats de
    la partie close."""
    headers: dict[str, str] = room["headers"]
    if action == "results":
        return client.get(f"/results/{room['public_token']}")
    if action == "read":
        return client.get(f"/rooms/{room['code']}", headers=headers)
    game: JsonObject = room["game"]
    return place(
        client, room["code"], game["current_item"]["id"], game["tiers"][0]["id"], 0, headers
    )


@pytest.mark.parametrize("action", ["read", "place", "results"])
def test_the_number_of_queries_does_not_grow_with_the_items(
    auth_client: TestClient, db_session: Session, action: str
):
    counts: list[int] = []
    for email, tile_count in (("small@example.com", 3), ("large@example.com", 10)):
        room: JsonObject = played_room(auth_client, db_session, email, tile_count)
        if action == "results":
            closed: JsonObject = play_and_close(auth_client, room["code"], room["headers"])
            room["public_token"] = closed["past_games"][0]["public_token"]
        with counted_queries(db_session) as statements:
            response: Response = send(auth_client, room, action)
        assert response.status_code == 200
        counts.append(len(statements))

    # Le plateau a 3 puis 10 items : autant de requêtes dans les deux cas
    assert counts[0] == counts[1], counts
