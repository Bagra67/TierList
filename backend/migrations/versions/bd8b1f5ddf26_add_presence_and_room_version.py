"""add presence and room version

Revision ID: bd8b1f5ddf26
Revises: 0a183946a488
Create Date: 2026-10-15 19:26:43.110387

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd8b1f5ddf26"
down_revision: str | Sequence[str] | None = "0a183946a488"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Personne n'est connecté tant que son canal temps réel n'est pas ouvert
    op.add_column(
        "participants",
        sa.Column("connected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "rooms", sa.Column("version", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("rooms", "version")
    op.drop_column("participants", "connected")
