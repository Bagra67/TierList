"""Types de champs communs à plusieurs schémas."""

from typing import Annotated

from pydantic import StringConstraints

from app.constants.auth import DISPLAY_NAME_MAX_LENGTH

# Nom affiché d'un compte ou pseudo d'un invité : espaces de début et de fin retirés, 1 à 50
# caractères
DisplayName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH),
]
