import json
import sys
from pathlib import Path

BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)
OPENAPI_PATH = BACKEND_DIR / "openapi.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def render_openapi() -> str:
    from app.main import api_app

    return json.dumps(api_app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8", newline="\n")
    print(f"OpenAPI schema written to {OPENAPI_PATH.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
