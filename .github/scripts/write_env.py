"""Writes the .env of the pod from the environment of the deployment job (GitHub secrets and
variables). See docs/technical/deployment.md.

Usage: python3 .github/scripts/write_env.py <output file>

The pod start script sources the file with bash (set -a; . .env): every value is single-quoted,
so that no character of a secret ($, `, spaces, quotes...) is interpreted by the shell.
"""

import os
import sys
from collections.abc import Mapping
from pathlib import Path

# Must be set in the GitHub environment (secret or variable): the application cannot run without
REQUIRED = (
    "APP_RELEASE",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "JWT_SECRET_KEY",
    "FRONTEND_BASE_URL",
    "TRUSTED_PROXY_IPS",
    "IMAGE_S3_ENDPOINT_URL",
    "IMAGE_S3_BUCKET",
    "IMAGE_S3_REGION",
    "IMAGE_S3_ACCESS_KEY_ID",
    "IMAGE_S3_SECRET_ACCESS_KEY",
    "IMAGE_PUBLIC_BASE_URL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
)

# Written only when set: the application has a default (or works without, like Google sign-in)
OPTIONAL = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "LOG_LEVEL",
    "MAINTENANCE_ENABLED",
    "MAINTENANCE_HOUR_UTC",
)

# Same value in every deployed environment: served over HTTPS (Cloudflare Tunnel)
FIXED = {"AUTH_COOKIE_SECURE": "true"}


class EnvFileError(ValueError):
    pass


def quote(value: str) -> str:
    """Single-quoted for bash: a quote inside the value ends the quoting, is escaped, then the
    quoting starts again."""
    return "'" + value.replace("'", "'\\''") + "'"


def render_env_file(environ: Mapping[str, str]) -> str:
    missing: list[str] = [name for name in REQUIRED if not environ.get(name)]
    if missing:
        raise EnvFileError(f"Missing in the GitHub environment: {', '.join(missing)}")
    values: dict[str, str] = {name: environ[name] for name in REQUIRED}
    values.update({name: environ[name] for name in OPTIONAL if environ.get(name)})
    values.update(FIXED)
    for name, value in values.items():
        # A line break would end the variable in the middle of its value
        if "\n" in value or "\r" in value:
            raise EnvFileError(f"{name} contains a line break")
    return "".join(f"{name}={quote(value)}\n" for name, value in values.items())


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 .github/scripts/write_env.py <output file>", file=sys.stderr)
        return 2
    try:
        content: str = render_env_file(os.environ)
    except EnvFileError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    output: Path = Path(sys.argv[1])
    # Only the job user can read the secrets written there
    output.touch(mode=0o600)
    output.write_text(content, encoding="utf-8", newline="\n")
    print(f"{output}: {len(content.splitlines())} variables written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
