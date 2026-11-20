"""list deleted templates and log restores and purges

Revision ID: f3ed645c1e5c
Revises: 3cc4d74966c1
Create Date: 2026-11-19 20:13:40.101372

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

ACTION_KINDS_BEFORE = ("dismiss", "hide", "unhide", "delete", "ban", "lift_ban")
ACTION_KINDS_AFTER = (*ACTION_KINDS_BEFORE, "restore", "purge")
ACTION_KIND_CONSTRAINT = "ck_moderation_actions_moderation_action_kind"


# revision identifiers, used by Alembic.
revision: str = "f3ed645c1e5c"
down_revision: str | Sequence[str] | None = "3cc4d74966c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_action_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f(ACTION_KIND_CONSTRAINT), "moderation_actions", type_="check")
    allowed: str = ", ".join(f"'{kind}'" for kind in kinds)
    op.create_check_constraint(
        op.f(ACTION_KIND_CONSTRAINT), "moderation_actions", sa.text(f"action IN ({allowed})")
    )


def upgrade() -> None:
    """Upgrade schema."""
    _replace_action_kinds(ACTION_KINDS_AFTER)
    op.add_column("templates", sa.Column("deletion_reason", sa.String(length=500), nullable=True))
    op.execute(
        """
        UPDATE templates SET deletion_reason = deletions.reason
        FROM (
            SELECT DISTINCT ON (target_id) target_id, reason
            FROM moderation_actions
            WHERE target_type = 'template' AND action = 'delete'
            ORDER BY target_id, created_at DESC, id DESC
        ) AS deletions
        WHERE deletions.target_id = templates.id AND templates.deleted_at IS NOT NULL
        """
    )
    op.create_index(
        "ix_templates_deleted",
        "templates",
        ["deleted_at", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_templates_deleted", table_name="templates")
    op.drop_column("templates", "deletion_reason")
    op.execute("DELETE FROM moderation_actions WHERE action IN ('restore', 'purge')")
    _replace_action_kinds(ACTION_KINDS_BEFORE)
