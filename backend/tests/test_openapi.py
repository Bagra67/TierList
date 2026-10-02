from scripts.export_openapi import OPENAPI_PATH, render_openapi


def test_openapi_schema_is_up_to_date():
    # openapi.json est le contrat d'API dont le frontend génère ses types (pnpm gen:api).
    committed = OPENAPI_PATH.read_text(encoding="utf-8")
    assert committed == render_openapi(), (
        "backend/openapi.json is out of date: run `uv run python scripts/export_openapi.py` "
        "(in backend/), then `pnpm gen:api` (in frontend/), and commit both files."
    )
