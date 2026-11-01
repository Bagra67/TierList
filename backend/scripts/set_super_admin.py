"""Donne ou retire le rôle super admin à un compte existant (US-1.1).

Usage (dans backend/) :
    uv run python scripts/set_super_admin.py <email>            # donne le rôle
    uv run python scripts/set_super_admin.py <email> --revoke   # le retire

Pour le développement local : le pod de production n'a pas de shell, le rôle s'y donne par une
requête SQL (docs/technical/deployment.md). Le changement vaut dès la requête suivante côté
serveur ; l'interface l'affiche après un rechargement de la page.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

# Dossier backend/ : le premier dossier parent qui contient alembic.ini
BACKEND_DIR = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "alembic.ini").is_file()
)

# Permet `python scripts/set_super_admin.py` : le paquet `app` est dans backend/.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant or revoke the super admin role.")
    parser.add_argument("email", help="email address of an existing account")
    parser.add_argument("--revoke", action="store_true", help="remove the role instead")
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    from app.core.logging import configure_logging, get_logging_settings
    from app.db.session import get_engine
    from app.exceptions.auth import UserNotFoundError
    from app.models.enums import UserRole
    from app.services.super_admins import set_super_admin

    options: argparse.Namespace = parse_arguments(arguments)
    configure_logging(get_logging_settings().log_level)
    try:
        role: UserRole = set_super_admin(
            lambda: Session(get_engine()), options.email, granted=not options.revoke
        )
    except UserNotFoundError:
        print(f"No account with the email {options.email}", file=sys.stderr)
        return 1
    print(f"Role of {options.email}: {role}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
