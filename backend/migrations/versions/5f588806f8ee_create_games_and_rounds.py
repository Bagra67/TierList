"""create games and rounds

Revision ID: 5f588806f8ee
Revises: 4eaf2e07846b
Create Date: 2026-10-16 17:21:06.484871

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f588806f8ee"
down_revision: str | Sequence[str] | None = "4eaf2e07846b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "games",
        # SET NULL : une partie survit à sa salle
        sa.Column("room_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        # Les contraintes CHECK des valeurs (ck_games_game_status, ck_games_item_order) sont
        # créées par les types Enum
        sa.Column(
            "status",
            sa.Enum(
                "in_round",
                "cooldown",
                "closed",
                name="game_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "item_order",
            sa.Enum(
                "template", "random", name="item_order", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("admin_plays", sa.Boolean(), nullable=False),
        sa.Column("current_round_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_games_room_id_rooms"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["template_snapshots.id"],
            name=op.f("fk_games_snapshot_id_template_snapshots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
    )
    op.create_index(op.f("ix_games_snapshot_id"), "games", ["snapshot_id"], unique=False)
    # Au plus une partie en cours par salle
    op.create_index(
        "uq_games_room_id_in_progress",
        "games",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'closed'"),
    )
    op.create_table(
        "rounds",
        sa.Column("game_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("snapshot_tile_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], name=op.f("fk_rounds_game_id_games"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_tile_id"],
            ["snapshot_tiles.id"],
            name=op.f("fk_rounds_snapshot_tile_id_snapshot_tiles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rounds")),
        # Un tour par rang et un tour par tuile dans une partie
        sa.UniqueConstraint("game_id", "number", name=op.f("uq_rounds_game_id_number")),
        sa.UniqueConstraint(
            "game_id", "snapshot_tile_id", name=op.f("uq_rounds_game_id_snapshot_tile_id")
        ),
    )
    op.create_index(
        op.f("ix_rounds_snapshot_tile_id"), "rounds", ["snapshot_tile_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_rounds_snapshot_tile_id"), table_name="rounds")
    op.drop_table("rounds")
    op.drop_index(
        "uq_games_room_id_in_progress",
        table_name="games",
        postgresql_where=sa.text("status <> 'closed'"),
    )
    op.drop_index(op.f("ix_games_snapshot_id"), table_name="games")
    op.drop_table("games")
