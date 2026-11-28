"""template copies

Revision ID: d7a3f2c81e45
Revises: c4e1a7d29b56
Create Date: 2026-11-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7a3f2c81e45"
down_revision: str | Sequence[str] | None = "c4e1a7d29b56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "templates",
        sa.Column("forks_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "template_ancestors",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("ancestor_id", sa.Uuid(), nullable=True),
        sa.Column("ancestor_name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["ancestor_id"],
            ["templates.id"],
            name=op.f("fk_template_ancestors_ancestor_id_templates"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_template_ancestors_template_id_templates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("template_id", "depth", name=op.f("pk_template_ancestors")),
    )
    op.create_index(
        op.f("ix_template_ancestors_ancestor_id"),
        "template_ancestors",
        ["ancestor_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_template_ancestors_ancestor_id"), table_name="template_ancestors")
    op.drop_table("template_ancestors")
    op.drop_column("templates", "forks_allowed")
