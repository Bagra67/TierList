"""add moderation reason to images

Revision ID: c4f1a7d29e30
Revises: 86488d6e1228
Create Date: 2026-11-03 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f1a7d29e30"
down_revision: str | Sequence[str] | None = "86488d6e1228"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("images", sa.Column("moderation_reason", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("images", "moderation_reason")
