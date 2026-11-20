"""official templates: the site's account, featuring, edit lease and editorial log actions

Revision ID: 7b2e4c9d1a03
Revises: f3ed645c1e5c
Create Date: 2026-11-20 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

ACTION_KINDS_BEFORE = (
    "dismiss",
    "hide",
    "unhide",
    "delete",
    "ban",
    "lift_ban",
    "restore",
    "purge",
)
EDITORIAL_ACTION_KINDS = ("create", "edit", "publish", "unpublish", "feature", "unfeature")
ACTION_KINDS_AFTER = (*ACTION_KINDS_BEFORE, *EDITORIAL_ACTION_KINDS)
ACTION_KIND_CONSTRAINT = "ck_moderation_actions_moderation_action_kind"
OFFICIAL_ACCOUNT_ID = "00000000-0000-4000-8000-0000000000ff"
EDITING_BY_FOREIGN_KEY = "fk_templates_editing_by_id_users"


# revision identifiers, used by Alembic.
revision: str = "7b2e4c9d1a03"
down_revision: str | Sequence[str] | None = "f3ed645c1e5c"
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
    op.alter_column("moderation_actions", "action", existing_type=sa.String(8), type_=sa.String(9))
    _replace_action_kinds(ACTION_KINDS_AFTER)
    op.alter_column("moderation_actions", "reason", existing_type=sa.String(500), nullable=True)
    op.add_column("templates", sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("templates", sa.Column("editing_by_id", sa.Uuid(), nullable=True))
    op.add_column(
        "templates", sa.Column("editing_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "templates",
        sa.Column("edit_logged", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_foreign_key(
        op.f(EDITING_BY_FOREIGN_KEY),
        "templates",
        "users",
        ["editing_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        f"""
        INSERT INTO users (id, email, display_name)
        VALUES ('{OFFICIAL_ACCOUNT_ID}', 'official@tierlist.invalid', 'TierList')
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DELETE FROM users WHERE id = '{OFFICIAL_ACCOUNT_ID}'")
    op.drop_constraint(op.f(EDITING_BY_FOREIGN_KEY), "templates", type_="foreignkey")
    op.drop_column("templates", "edit_logged")
    op.drop_column("templates", "editing_until")
    op.drop_column("templates", "editing_by_id")
    op.drop_column("templates", "featured_at")
    editorial: str = ", ".join(f"'{kind}'" for kind in EDITORIAL_ACTION_KINDS)
    op.execute(f"DELETE FROM moderation_actions WHERE action IN ({editorial})")
    op.execute("UPDATE moderation_actions SET reason = '' WHERE reason IS NULL")
    op.alter_column("moderation_actions", "reason", existing_type=sa.String(500), nullable=False)
    _replace_action_kinds(ACTION_KINDS_BEFORE)
    op.alter_column("moderation_actions", "action", existing_type=sa.String(9), type_=sa.String(8))
