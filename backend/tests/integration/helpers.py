"""Outils partagés par les tests d'intégration (les fixtures sont dans conftest.py)."""

import re
from urllib.parse import parse_qs, urlparse

from app.services.email import Email


def link_token(email: Email) -> str:
    """Token du lien contenu dans un email (paramètre token de l'URL)."""
    match = re.search(r"https?://\S+", email.text)
    assert match is not None, "aucun lien dans l'email"
    return parse_qs(urlparse(match.group()).query)["token"][0]
