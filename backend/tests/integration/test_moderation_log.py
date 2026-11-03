from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.enums import ModerationActionKind, ModerationTargetType, UserRole
from app.models.moderation_action import ModerationAction
from app.models.user import User
from app.services.maintenance import purge_moderation_log
from app.services.moderation_log import ModerationLogService

pytestmark = pytest.mark.integration


@pytest.fixture
def nina(db_session: Session) -> User:
    super_admin: User = User(
        email="nina@example.com", display_name="Nina", role=UserRole.SUPER_ADMIN
    )
    db_session.add(super_admin)
    db_session.flush()
    return super_admin


def record_hide(db_session: Session, actor: User, label: str = 'Template "Top 10"') -> None:
    ModerationLogService(db_session, get_settings()).record(
        actor,
        ModerationActionKind.HIDE,
        ModerationTargetType.TEMPLATE,
        None,
        label,
        "Harassment",
    )


def logged_actions(db_session: Session) -> list[ModerationAction]:
    return list(db_session.scalars(select(ModerationAction)).all())


def test_record_writes_who_when_what_and_why(db_session: Session, nina: User):
    ModerationLogService(db_session, get_settings()).record(
        nina,
        ModerationActionKind.HIDE,
        ModerationTargetType.TEMPLATE,
        nina.id,
        'Template "Top 10"',
        "Harassment",
    )

    [entry] = logged_actions(db_session)
    assert entry.actor_id == nina.id
    assert entry.actor_name == "Nina"
    assert entry.action == ModerationActionKind.HIDE
    assert entry.target_type == ModerationTargetType.TEMPLATE
    assert entry.target_id == nina.id
    assert entry.target_label == 'Template "Top 10"'
    assert entry.reason == "Harassment"
    assert entry.created_at is not None


def test_record_leaves_the_transaction_to_the_action(db_session: Session, nina: User):
    with pytest.raises(RuntimeError), db_session.begin_nested():
        record_hide(db_session, nina)
        raise RuntimeError("the moderation action failed")

    assert logged_actions(db_session) == []


def test_deleting_the_super_admin_account_keeps_the_entry_and_the_name(
    db_session: Session, nina: User
):
    record_hide(db_session, nina)

    db_session.delete(nina)
    db_session.flush()
    db_session.expire_all()

    [entry] = logged_actions(db_session)
    assert entry.actor_id is None
    assert entry.actor_name == "Nina"


def test_the_purge_deletes_the_entries_older_than_the_retention_only(
    db_session: Session, nina: User
):
    record_hide(db_session, nina, label="Old")
    record_hide(db_session, nina, label="Recent")
    old, recent = sorted(logged_actions(db_session), key=lambda entry: entry.target_label)
    old.created_at = datetime.now(UTC) - timedelta(days=1096)
    recent.created_at = datetime.now(UTC) - timedelta(days=1094)
    db_session.flush()

    retention_3_years: Settings = get_settings().model_copy(
        update={"moderation_log_retention_days": 1095}
    )
    purged_count: int = purge_moderation_log(lambda: nullcontext(db_session), retention_3_years)

    assert purged_count == 1
    assert [entry.target_label for entry in logged_actions(db_session)] == ["Recent"]
