"""Langues des emails, les mêmes que celles de l'interface (frontend/src/constants/i18n.ts)."""

from typing import Literal

Language = Literal["fr", "en"]
# Langue des emails quand le frontend n'en indique pas
DEFAULT_LANGUAGE: Language = "fr"
