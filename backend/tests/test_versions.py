import json
import tomllib
from pathlib import Path

from app.main import app

# Racine du dépôt : le premier dossier parent qui contient à la fois backend/ et frontend/
REPO_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "backend").is_dir() and (parent / "frontend").is_dir()
)


def test_versions_are_in_sync():
    # Une seule version pour tout le dépôt (docs/technical/releasing.md) :
    # scripts/prepare-release.sh met à jour ces trois valeurs, et le workflow Release crée le
    # tag vX.Y.Z à partir d'elles.
    pyproject_path = REPO_ROOT / "backend" / "pyproject.toml"
    package_json_path = REPO_ROOT / "frontend" / "package.json"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    package_json = json.loads(package_json_path.read_text(encoding="utf-8"))

    assert app.version == pyproject["project"]["version"] == package_json["version"]
