import pytest

from app.api.dependencies import get_current_super_admin
from app.constants.error_codes import ErrorCode
from app.exceptions.http import AppHTTPException
from app.models.enums import UserRole
from app.models.user import User


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
