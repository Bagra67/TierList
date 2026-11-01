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


def test_another_account_is_refused_with_a_403():
    with pytest.raises(AppHTTPException) as exc_info:
        get_current_super_admin(make_user(UserRole.USER))

    # 403 et non 401 : le compte est connecté, le frontend ne doit pas rafraîchir sa session
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == ErrorCode.SUPER_ADMIN_REQUIRED
