from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError


def violates_unique(exc: IntegrityError, constraint_name: str) -> bool:
    return (
        isinstance(exc.orig, UniqueViolation) and exc.orig.diag.constraint_name == constraint_name
    )
