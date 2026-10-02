from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings

# Sans délai, une connexion vers une base arrêtée peut bloquer la requête très longtemps.
CONNECT_TIMEOUT_SECONDS = 3


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


def get_db_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def ping_database(session: Session) -> None:
    session.execute(text("SELECT 1"))
