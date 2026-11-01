import json
from typing import Any

from scripts.export_openapi import OPENAPI_PATH, render_openapi


def test_openapi_schema_is_up_to_date():
    # openapi.json est le contrat d'API dont le frontend génère ses types (pnpm gen:api).
    committed = OPENAPI_PATH.read_text(encoding="utf-8")
    assert committed == render_openapi(), (
        "backend/openapi.json is out of date: run `uv run python scripts/export_openapi.py` "
        "(in backend/), then `pnpm gen:api` (in frontend/), and commit both files."
    )


def request_schema_names(openapi: dict[str, Any]) -> set[str]:
    """Noms des schémas envoyés par le client (corps des requêtes), et des schémas qu'ils
    contiennent."""
    schemas: dict[str, Any] = openapi["components"]["schemas"]
    pending: list[Any] = [
        operation.get("requestBody", {})
        for path_item in openapi["paths"].values()
        for operation in path_item.values()
    ]
    names: set[str] = set()
    while pending:
        node: Any = pending.pop()
        if isinstance(node, dict):
            reference: str | None = node.get("$ref")
            if reference is not None:
                name: str = reference.rsplit("/", 1)[-1]
                if name not in names:
                    names.add(name)
                    pending.append(schemas[name])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return names


def test_no_request_can_set_the_role():
    # Le rôle super admin n'est jamais attribué par l'API (US-1.1) : aucun corps de requête ne
    # doit pouvoir le contenir.
    openapi: dict[str, Any] = json.loads(render_openapi())
    schemas: dict[str, Any] = openapi["components"]["schemas"]
    names: set[str] = request_schema_names(openapi)

    # Garde-fou : le parcours trouve bien les schémas des requêtes
    assert "RegisterRequest" in names
    for name in names:
        assert "role" not in schemas[name].get("properties", {}), name
