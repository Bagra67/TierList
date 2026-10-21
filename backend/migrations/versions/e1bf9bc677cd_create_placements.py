"""create placements

Revision ID: e1bf9bc677cd
Revises: 5f588806f8ee
Create Date: 2026-10-17 11:27:47.823407

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1bf9bc677cd"
down_revision: str | Sequence[str] | None = "5f588806f8ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "placements",
        sa.Column("game_id", sa.Uuid(), nullable=False),
        # CASCADE : les placements d'un participant retiré disparaissent avec sa place
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_tile_id", sa.Uuid(), nullable=False),
        # La contrainte CHECK des valeurs (ck_placements_placement_phase) est créée par le type Enum
        sa.Column(
            "phase",
            sa.Enum(
                "round", "final", name="placement_phase", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("snapshot_tier_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint(
            "phase = 'round' OR snapshot_tier_id IS NOT NULL",
            name=op.f("ck_placements_final_not_absent"),
        ),
        sa.CheckConstraint(
            "(snapshot_tier_id IS NULL) = (position IS NULL) AND position >= 0",
            name=op.f("ck_placements_tier_and_position"),
        ),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], name=op.f("fk_placements_game_id_games"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participants.id"],
            name=op.f("fk_placements_participant_id_participants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_tier_id"],
            ["snapshot_tiers.id"],
            name=op.f("fk_placements_snapshot_tier_id_snapshot_tiers"),
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_tile_id"],
            ["snapshot_tiles.id"],
            name=op.f("fk_placements_snapshot_tile_id_snapshot_tiles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_placements")),
        sa.UniqueConstraint(
            "game_id",
            "participant_id",
            "snapshot_tile_id",
            "phase",
            name=op.f("uq_placements_game_id_participant_id_snapshot_tile_id_phase"),
        ),
    )
    op.create_index(op.f("ix_placements_game_id"), "placements", ["game_id"], unique=False)
    op.create_index(
        op.f("ix_placements_participant_id"), "placements", ["participant_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_placements_participant_id"), table_name="placements")
    op.drop_index(op.f("ix_placements_game_id"), table_name="placements")
    op.drop_table("placements")
