import logging
import os
import sys
import time
from pathlib import Path

from sqlalchemy.orm import Session

BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _show_only_seed_progress_logs() -> None:
    from app.core.logging import configure_logging

    configure_logging("WARNING")
    logging.getLogger("app.seed").setLevel(logging.INFO)


def main() -> int:
    from app.core.config import Settings, get_settings
    from app.db.session import get_engine
    from app.seed.guard import SeedRefusedError, check_database, seed_password
    from app.seed.run import SeedSummary, run_seed
    from app.seed.sizes import FULL_SIZE
    from app.services.image_storage import create_image_storage

    _show_only_seed_progress_logs()
    settings: Settings = get_settings()
    try:
        check_database(settings.postgres_db)
        password: str = seed_password(settings.postgres_db, os.environ.get("SEED_PASSWORD"))
    except SeedRefusedError as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Seeding the database {settings.postgres_db!r} on {settings.postgres_host}", flush=True)
    started: float = time.monotonic()
    with Session(get_engine()) as session:
        summary: SeedSummary = run_seed(
            session, settings, create_image_storage(settings), FULL_SIZE, password
        )
    print(
        f"Removed: {summary.removed.accounts} accounts, {summary.removed.games} games, "
        f"{summary.removed.images} images"
    )
    print(
        f"Created: {summary.accounts} accounts, {summary.templates} templates, "
        f"{summary.images} images, {summary.closed_games} closed games, "
        f"{summary.open_rooms} open rooms, {summary.moderation_actions} moderation log entries, "
        f"{summary.reports} open reports"
    )
    print(f"Database {settings.postgres_db!r} seeded in {time.monotonic() - started:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
