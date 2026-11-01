"""add created_at index to images

Revision ID: 4840e3c37d23
Revises: 1c5aea95404b
Create Date: 2026-11-01 15:23:39.093461

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4840e3c37d23"
down_revision: str | Sequence[str] | None = "1c5aea95404b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Derniers envois des super admins (#125) : toutes les images, des plus récentes aux plus
    # anciennes
    op.create_index("ix_images_created_at", "images", ["created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_images_created_at", table_name="images")
