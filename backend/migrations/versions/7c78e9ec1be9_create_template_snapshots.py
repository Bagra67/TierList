"""create template snapshots

Revision ID: 7c78e9ec1be9
Revises: a2ee58bb5b26
Create Date: 2026-10-11 13:40:40.797812

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c78e9ec1be9"
down_revision: str | Sequence[str] | None = "a2ee58bb5b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "template_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "taken_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        # SET NULL : purger le template ou supprimer le compte garde les snapshots
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_template_snapshots_template_id_templates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_snapshots")),
    )
    op.create_index(
        op.f("ix_template_snapshots_template_id"),
        "template_snapshots",
        ["template_id"],
        unique=False,
    )
    op.create_table(
        "snapshot_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["template_snapshots.id"],
            name=op.f("fk_snapshot_tiers_snapshot_id_template_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_snapshot_tiers")),
    )
    op.create_index(
        op.f("ix_snapshot_tiers_snapshot_id"), "snapshot_tiers", ["snapshot_id"], unique=False
    )
    op.create_table(
        "snapshot_tiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=True),
        sa.Column("image_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["template_snapshots.id"],
            name=op.f("fk_snapshot_tiles_snapshot_id_template_snapshots"),
            ondelete="CASCADE",
        ),
        # Pas de ON DELETE, comme tiles.image_id : seul le ramasse-miettes efface une image
        sa.ForeignKeyConstraint(
            ["image_id"], ["images.id"], name=op.f("fk_snapshot_tiles_image_id_images")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_snapshot_tiles")),
    )
    op.create_index(
        op.f("ix_snapshot_tiles_snapshot_id"), "snapshot_tiles", ["snapshot_id"], unique=False
    )
    op.create_index(
        op.f("ix_snapshot_tiles_image_id"), "snapshot_tiles", ["image_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_snapshot_tiles_image_id"), table_name="snapshot_tiles")
    op.drop_index(op.f("ix_snapshot_tiles_snapshot_id"), table_name="snapshot_tiles")
    op.drop_table("snapshot_tiles")
    op.drop_index(op.f("ix_snapshot_tiers_snapshot_id"), table_name="snapshot_tiers")
    op.drop_table("snapshot_tiers")
    op.drop_index(op.f("ix_template_snapshots_template_id"), table_name="template_snapshots")
    op.drop_table("template_snapshots")
