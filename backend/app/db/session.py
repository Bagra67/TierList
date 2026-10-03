from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


def get_db_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def ping_database(session: Session) -> None:
    session.execute(text("SELECT 1"))
