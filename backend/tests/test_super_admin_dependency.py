import ast
from pathlib import Path

import pytest

from app.api.dependencies import get_current_super_admin
from app.constants.error_codes import ErrorCode
from app.exceptions.http import AppHTTPException
from app.models.enums import UserRole
from app.models.user import User

APP_DIR: Path = Path(__file__).resolve().parents[1] / "app"
SUPER_ADMIN_SERVICE: str = "app.services.super_admins"


def imports_the_super_admin_service(source_file: Path) -> bool:
    tree: ast.Module = ast.parse(source_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == SUPER_ADMIN_SERVICE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == SUPER_ADMIN_SERVICE:
                return True
            if node.module == "app.services" and any(
                alias.name == "super_admins" for alias in node.names
            ):
                return True
    return False


def make_user(role: UserRole) -> User:
    return User(email="alice@example.com", display_name="Alice", role=role)


def test_a_super_admin_is_let_through():
    super_admin: User = make_user(UserRole.SUPER_ADMIN)

    assert get_current_super_admin(super_admin) is super_admin


def test_another_account_gets_a_403_not_a_401_so_the_frontend_does_not_refresh():
    with pytest.raises(AppHTTPException) as exc_info:
        get_current_super_admin(make_user(UserRole.USER))

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == ErrorCode.SUPER_ADMIN_REQUIRED


def test_the_application_never_grants_the_role():
    importers: list[Path] = [
        source_file
        for source_file in APP_DIR.rglob("*.py")
        if imports_the_super_admin_service(source_file)
    ]

    assert importers == []
