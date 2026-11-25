"""create template favorites

Revision ID: c4e1a7d29b56
Revises: 7b2e4c9d1a03
Create Date: 2026-11-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e1a7d29b56"
down_revision: str | Sequence[str] | None = "7b2e4c9d1a03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "template_favorites",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_template_favorites_template_id_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_template_favorites_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("template_id", "user_id", name=op.f("pk_template_favorites")),
    )
    op.create_index(
        "ix_template_favorites_user_id_created_at",
        "template_favorites",
        ["user_id", "created_at", "template_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_template_favorites_user_id_created_at", table_name="template_favorites")
    op.drop_table("template_favorites")
