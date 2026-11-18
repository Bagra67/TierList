"""index the newest public templates

Revision ID: 3cc4d74966c1
Revises: a9b8f14a856a
Create Date: 2026-11-18 12:37:45.803145

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

LISTED_TEMPLATES = "visibility = 'public' AND moderation = 'none' AND deleted_at IS NULL"


# revision identifiers, used by Alembic.
revision: str = "3cc4d74966c1"
down_revision: str | Sequence[str] | None = "a9b8f14a856a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_templates_listed_newest",
        "templates",
        [sa.literal_column("first_made_public_at DESC"), sa.literal_column("id DESC")],
        unique=False,
        postgresql_where=sa.text(LISTED_TEMPLATES),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_templates_listed_newest", table_name="templates")
