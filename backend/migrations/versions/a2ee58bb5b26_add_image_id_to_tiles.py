"""add image_id to tiles

Revision ID: a2ee58bb5b26
Revises: ef5839ce8066
Create Date: 2026-10-10 20:21:56.235947

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2ee58bb5b26"
down_revision: str | Sequence[str] | None = "ef5839ce8066"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable : les tuiles existantes n'ont qu'un texte
    op.add_column("tiles", sa.Column("image_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_tiles_image_id"), "tiles", ["image_id"], unique=False)
    op.create_foreign_key(op.f("fk_tiles_image_id_images"), "tiles", "images", ["image_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_tiles_image_id_images"), "tiles", type_="foreignkey")
    op.drop_index(op.f("ix_tiles_image_id"), table_name="tiles")
    op.drop_column("tiles", "image_id")
