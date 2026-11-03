import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR: Path = Path(__file__).resolve().parents[1]

DEFERRED_PACKAGES: tuple[str, ...] = ("boto3", "botocore")


def test_starting_the_app_does_not_load_the_s3_client():
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


@pytest.mark.parametrize(
    ("trusted_proxy_ips", "guard_installed"),
    [
        pytest.param("10.0.0.7", True, id="proxies-set"),
        pytest.param("", False, id="no-proxy"),
    ],
)
def test_the_app_installs_the_proxy_guard_only_when_proxies_are_set(
    trusted_proxy_ips: str, guard_installed: bool
):
    script: str = (
        "from app.main import app\n"
        "print(' '.join(middleware.cls.__name__ for middleware in app.user_middleware))\n"
    )
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env={**os.environ, "TRUSTED_PROXY_IPS": trusted_proxy_ips},
        capture_output=True,
        text=True,
        check=True,
    )
    assert ("TrustedProxyMiddleware" in completed.stdout.split()) is guard_installed
