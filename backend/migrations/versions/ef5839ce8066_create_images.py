"""create images

Revision ID: ef5839ce8066
Revises: d34f53ab3105
Create Date: 2026-10-10 20:00:03.459053

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef5839ce8066"
down_revision: str | Sequence[str] | None = "d34f53ab3105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        # La contrainte CHECK des statuts (ck_images_image_status) est créée par le type Enum
        sa.Column(
            "status",
            sa.Enum(
                "visible",
                "hidden",
                "deleted",
                name="image_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_images_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_images_storage_key")),
    )
    op.create_index(
        "ix_images_owner_id_created_at", "images", ["owner_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_images_sha256"), "images", ["sha256"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_images_sha256"), table_name="images")
    op.drop_index("ix_images_owner_id_created_at", table_name="images")
    op.drop_table("images")
