"""add updated_at to user tables

Revision ID: d34f53ab3105
Revises: 855df2a2ea2b
Create Date: 2026-10-10 09:49:32.921915

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d34f53ab3105"
down_revision: str | Sequence[str] | None = "855df2a2ea2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables passées au TimestampMixin (app/db/mixins.py)
USER_TABLES: tuple[str, ...] = ("users", "refresh_tokens", "oauth_accounts")


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in USER_TABLES:
        # Le server_default remplit aussi les lignes existantes
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("clock_timestamp()"),
                nullable=False,
            ),
        )
        # Ajouté à la main : autogenerate ne compare pas les server_default, mais le mixin
        # déclare clock_timestamp() et non plus now()
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("clock_timestamp()"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in USER_TABLES:
        op.alter_column(
            table_name,
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.text("now()"),
        )
        op.drop_column(table_name, "updated_at")
