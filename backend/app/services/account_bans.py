import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions.auth import UserNotFoundError
from app.exceptions.moderation import (
    AccountNotBannedError,
    BanEndInPastError,
    CannotBanSuperAdminError,
)
from app.models.account_ban import AccountBan
from app.models.enums import ModerationActionKind, ModerationTargetType
from app.models.user import User
from app.repositories import account_bans as account_ban_repository
from app.repositories import refresh_tokens as refresh_token_repository
from app.repositories import users as user_repository
from app.services.moderation_log import ModerationLogService

logger = logging.getLogger(__name__)


class AccountBanService:
    def __init__(self, session: Session, moderation_log: ModerationLogService) -> None:
        self._session = session
        self._moderation_log = moderation_log

    def active_ban(self, user_id: uuid.UUID) -> AccountBan | None:
        return account_ban_repository.get_active_ban(self._session, user_id, datetime.now(UTC))

    def past_bans(self, user_id: uuid.UUID) -> list[AccountBan]:
        return account_ban_repository.list_past_bans(self._session, user_id, datetime.now(UTC))

    def banned_user_ids(self, user_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return account_ban_repository.banned_user_ids(self._session, user_ids, datetime.now(UTC))

    def ban(
        self,
        super_admin: User,
        user_id: uuid.UUID,
        reason: str,
        ends_at: datetime | None,
        after_ban: Callable[[uuid.UUID], None] | None = None,
    ) -> AccountBan:
        now: datetime = datetime.now(UTC)
        user: User = self._get_user_for_update(user_id)
        if user.is_super_admin:
            raise CannotBanSuperAdminError
        if ends_at is not None and ends_at <= now:
            raise BanEndInPastError
        current: AccountBan | None = account_ban_repository.get_active_ban(
            self._session, user.id, now
        )
        if current is not None:
            current.lifted_at = now
        ban: AccountBan = AccountBan(
            user_id=user.id,
            actor_id=super_admin.id,
            actor_name=super_admin.display_name,
            reason=reason,
            ends_at=ends_at,
        )
        account_ban_repository.add_ban(self._session, ban)
        refresh_token_repository.revoke_user_refresh_tokens(self._session, user.id, revoked_at=now)
        user.token_version += 1
        self._moderation_log.record(
            super_admin,
            ModerationActionKind.BAN,
            ModerationTargetType.ACCOUNT,
            user.id,
            user.display_name,
            reason,
        )
        self._session.commit()
        logger.info(
            "Compte banni : user_id=%s permanent=%s super_admin_id=%s",
            user.id,
            ends_at is None,
            super_admin.id,
        )
        if after_ban is not None:
            after_ban(user.id)
        return ban

    def lift(self, super_admin: User, user_id: uuid.UUID, reason: str) -> None:
        now: datetime = datetime.now(UTC)
        user: User = self._get_user_for_update(user_id)
        current: AccountBan | None = account_ban_repository.get_active_ban(
            self._session, user.id, now
        )
        if current is None:
            raise AccountNotBannedError
        current.lifted_at = now
        self._moderation_log.record(
            super_admin,
            ModerationActionKind.LIFT_BAN,
            ModerationTargetType.ACCOUNT,
            user.id,
            user.display_name,
            reason,
        )
        self._session.commit()
        logger.info("Bannissement levé : user_id=%s super_admin_id=%s", user.id, super_admin.id)

    def _get_user_for_update(self, user_id: uuid.UUID) -> User:
        user: User | None = user_repository.get_user_for_update(self._session, user_id)
        if user is None:
            raise UserNotFoundError
        return user
