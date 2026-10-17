"""Supprime définitivement les templates supprimés depuis plus de DELETED_TEMPLATE_RETENTION_DAYS.

Usage (dans backend/) : uv run python scripts/purge_deleted_templates.py
En production, l'application la lance aussi chaque nuit (MAINTENANCE_ENABLED, voir
docs/technical/deployment.md). Relancer la commande ne pose aucun problème : elle ne supprime
que ce qui a expiré.
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

# Dossier backend/ : le premier dossier parent qui contient alembic.ini
BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)

# Permet `python scripts/purge_deleted_templates.py` : le paquet `app` est dans backend/.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    from app.core.config import get_settings
    from app.core.logging import configure_logging, get_logging_settings
    from app.db.session import get_engine
    from app.services.maintenance import purge_deleted_templates

    configure_logging(get_logging_settings().log_level)
    purged_count: int = purge_deleted_templates(lambda: Session(get_engine()), get_settings())
    print(f"Deleted templates purged: {purged_count}")


if __name__ == "__main__":
    main()
