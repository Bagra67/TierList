"""add visibility to templates

Revision ID: 9b3e5d71c2a4
Revises: c4f1a7d29e30
Create Date: 2026-11-11 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3e5d71c2a4"
down_revision: str | Sequence[str] | None = "c4f1a7d29e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "templates",
        sa.Column(
            "visibility",
            sa.Enum(
                "private",
                "public",
                name="template_visibility",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'private'"),
            nullable=False,
        ),
    )
    op.add_column(
        "templates",
        sa.Column("first_made_public_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("templates", "first_made_public_at")
    op.drop_column("templates", "visibility")
