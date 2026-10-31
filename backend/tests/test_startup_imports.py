import subprocess
import sys
from pathlib import Path

BACKEND_DIR: Path = Path(__file__).resolve().parents[1]

# Chargés en différé (lazy import, PEP 810) : un import direct ajouté ailleurs annulerait le gain
DEFERRED_PACKAGES: tuple[str, ...] = ("boto3", "botocore")


def test_starting_the_app_does_not_load_the_s3_client():
    # Un sous-processus neuf : les autres tests ont pu charger boto3 dans ce processus-ci
    script: str = (
        "import sys\n"
        "import app.main\n"
        "print(' '.join(sorted({name.split('.')[0] for name in sys.modules})))\n"
    )
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    loaded_packages: set[str] = set(completed.stdout.split())
    assert loaded_packages.isdisjoint(DEFERRED_PACKAGES), (
        f"{sorted(loaded_packages & set(DEFERRED_PACKAGES))} loaded when the app starts: "
        "import them with `lazy import` (app/services/image_storage.py, app/services/images.py)."
    )
