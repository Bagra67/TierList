import sys
from pathlib import Path

from sqlalchemy.orm import Session

BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    from app.core.config import Settings, get_settings
    from app.core.logging import configure_logging, get_logging_settings
    from app.db.session import get_engine
    from app.services.image_storage import create_image_storage
    from app.services.maintenance import purge_unused_images

    configure_logging(get_logging_settings().log_level)
    settings: Settings = get_settings()
    purged_count: int = purge_unused_images(
        lambda: Session(get_engine()), settings, create_image_storage(settings)
    )
    print(f"Unused images purged: {purged_count}")


if __name__ == "__main__":
    main()
