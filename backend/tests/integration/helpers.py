"""Outils partagés par les tests d'intégration (les fixtures sont dans conftest.py)."""

import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from alembic.config import Config
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import URL
from sqlalchemy.orm import Session

from app.models.tile import Tile
from app.services.email import Email

# Dossier backend/ : le premier dossier parent qui contient alembic.ini
BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)


def alembic_config(database_url: URL) -> Config:
    """Configuration Alembic qui migre la base database_url."""
    # Config sans fichier .ini : évite qu'Alembic reconfigure le logging de pytest.
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    url = database_url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def link_token(email: Email) -> str:
    """Token du lien contenu dans un email (paramètre token de l'URL)."""
    match = re.search(r"https?://\S+", email.text)
    assert match is not None, "aucun lien dans l'email"
    return parse_qs(urlparse(match.group()).query)["token"][0]


# --- Salles (test_rooms.py, test_room_guests.py) ---------------------------------------------

PASSWORD = "correct horse battery staple"

# Objet JSON renvoyé par l'API : sa forme est vérifiée par les tests
JsonObject = dict[str, Any]


def register(client: TestClient, email: str) -> dict[str, str]:
    """Crée un compte et renvoie l'en-tête Authorization de son access token."""
    response: Response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_template(
    client: TestClient, db_session: Session, headers: dict[str, str], tile_count: int = 3
) -> str:
    """Template « Food » avec tile_count tuiles (ajoutées directement en base) ; renvoie son id."""
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


# --- Parties (test_game_reconnection.py, test_game_cooldown.py, test_game_close.py) ----------


def start_game(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    response: Response = client.post(f"/rooms/{code}/game", headers=headers)
    assert response.status_code == 201
    return response.json()


def next_item(client: TestClient, code: str, headers: dict[str, str]) -> JsonObject:
    """Le room admin termine le tour en cours (« Item suivant »)."""
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
    """Place une tuile ; sans headers, le cookie invité du client identifie le lecteur."""
    return client.put(
        f"/rooms/{code}/game/placements/{tile_id}",
        json={"tier_id": tier_id, "position": position},
        headers=headers,
    )


def board(room: JsonObject) -> list[tuple[str, str | None, int]]:
    """Plateau du lecteur : (nom du tier, texte de l'item, position), dans l'ordre renvoyé."""
    tier_names: dict[str, str] = {tier["id"]: tier["name"] for tier in room["game"]["tiers"]}
    return [
        (tier_names[placement["tier_id"]], placement["item"]["text"], placement["position"])
        for placement in room["game"]["own_placements"]
    ]
