"""Ramasse-miettes des images : efface celles qu'aucune tuile n'utilise depuis plus de
UNUSED_IMAGE_RETENTION_DAYS (docs/technical/images.md, « Cleanup »).

Usage (dans backend/) : uv run python scripts/purge_unused_images.py
À planifier une fois par jour sur le serveur, à côté de scripts/purge_deleted_templates.py : voir
TODO.md. Relancer la commande ne pose aucun problème : elle n'efface que ce qui a expiré.
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

# Dossier backend/ : le premier dossier parent qui contient alembic.ini
BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)

# Permet `python scripts/purge_unused_images.py` : le paquet `app` est dans backend/.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    from app.core.config import Settings, get_settings
    from app.core.logging import configure_logging, get_logging_settings
    from app.db.session import get_engine
    from app.services.image_storage import create_image_storage
    from app.services.images import ImageService

    configure_logging(get_logging_settings().log_level)
    settings: Settings = get_settings()
    with Session(get_engine()) as session:
        service: ImageService = ImageService(session, settings, create_image_storage(settings))
        purged_count: int = service.purge_unused()
    print(f"Unused images purged: {purged_count}")


if __name__ == "__main__":
    main()
