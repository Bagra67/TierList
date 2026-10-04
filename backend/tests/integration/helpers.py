"""Outils partagés par les tests d'intégration (les fixtures sont dans conftest.py)."""

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from alembic.config import Config
from sqlalchemy import URL

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
