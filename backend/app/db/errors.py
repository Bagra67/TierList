"""Lecture des erreurs de la base, communes à tous les services."""

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError


def violates_unique(exc: IntegrityError, constraint_name: str) -> bool:
    """L'erreur d'intégrité vient-elle de cette contrainte d'unicité ?"""
    return (
        isinstance(exc.orig, UniqueViolation) and exc.orig.diag.constraint_name == constraint_name
    )
