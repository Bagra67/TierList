"""add cooldown_ends_at to games

Revision ID: eaab3dece658
Revises: e1bf9bc677cd
Create Date: 2026-10-17 11:54:33.835744

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eaab3dece658"
down_revision: str | Sequence[str] | None = "e1bf9bc677cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("games", sa.Column("cooldown_ends_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "cooldown_ends_at")
