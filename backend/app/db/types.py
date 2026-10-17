"""Types de colonnes communs aux modèles."""

from enum import StrEnum

from sqlalchemy import Enum


def text_enum(enum_class: type[StrEnum], name: str) -> Enum:
    """Colonne texte avec une contrainte CHECK plutôt qu'un type ENUM PostgreSQL : ajouter une
    valeur ne demande pas d'ALTER TYPE (même choix que Image.status)."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )
