"""add moderation to templates

Revision ID: 507b5cf96d8d
Revises: 4840e3c37d23
Create Date: 2026-11-01 16:03:29.027305

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "507b5cf96d8d"
down_revision: str | Sequence[str] | None = "4840e3c37d23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Les modèles existants ne sont pas masqués : « none » par défaut, contrainte CHECK comprise
    op.add_column(
        "templates",
        sa.Column(
            "moderation",
            sa.Enum(
                "none",
                "hidden",
                name="template_moderation",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'none'"),
            nullable=False,
        ),
    )
    op.add_column("templates", sa.Column("moderation_reason", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("templates", "moderation_reason")
    op.drop_column("templates", "moderation")
