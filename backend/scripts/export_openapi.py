"""Exporte le contrat d'API (schéma OpenAPI de FastAPI) dans backend/openapi.json.

Usage (dans backend/) : uv run python scripts/export_openapi.py
Le frontend en génère ses types TypeScript (`pnpm gen:api`). Le test
tests/test_openapi.py vérifie que le fichier commité est à jour.
"""

import json
import sys
from pathlib import Path

# Dossier backend/ : le premier dossier parent qui contient alembic.ini
BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)
OPENAPI_PATH = BACKEND_DIR / "openapi.json"

# Permet `python scripts/export_openapi.py` : le paquet `app` est dans backend/.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def render_openapi() -> str:
    """Schéma OpenAPI sérialisé de façon déterministe (identique sous Windows et Linux)."""
    from app.main import app

    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8", newline="\n")
    print(f"OpenAPI schema written to {OPENAPI_PATH.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
