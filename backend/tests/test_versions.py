import json
import tomllib
from pathlib import Path

from app.main import api_app

REPO_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "backend").is_dir() and (parent / "frontend").is_dir()
)


def test_versions_are_in_sync():
    pyproject_path = REPO_ROOT / "backend" / "pyproject.toml"
    package_json_path = REPO_ROOT / "frontend" / "package.json"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    package_json = json.loads(package_json_path.read_text(encoding="utf-8"))

    assert api_app.version == pyproject["project"]["version"] == package_json["version"], (
        "versions out of sync: run scripts/prepare-release.sh (docs/technical/releasing.md); "
        "the Release workflow tags vX.Y.Z from these values"
    )
