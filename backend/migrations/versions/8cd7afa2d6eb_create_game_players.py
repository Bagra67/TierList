"""create game players

Revision ID: 8cd7afa2d6eb
Revises: eaab3dece658
Create Date: 2026-10-17 13:17:00.088569

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8cd7afa2d6eb"
down_revision: str | Sequence[str] | None = "eaab3dece658"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "game_players",
        sa.Column("game_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=50), nullable=False),
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
            ["game_id"],
            ["games.id"],
            name=op.f("fk_game_players_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_game_players_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_players")),
        sa.UniqueConstraint("game_id", "user_id", name=op.f("uq_game_players_game_id_user_id")),
    )
    op.create_index(op.f("ix_game_players_user_id"), "game_players", ["user_id"], unique=False)
    op.add_column("placements", sa.Column("player_id", sa.Uuid(), nullable=True))
    op.alter_column("placements", "participant_id", existing_type=sa.UUID(), nullable=True)
    op.create_index(op.f("ix_placements_player_id"), "placements", ["player_id"], unique=False)
    op.create_unique_constraint(
        op.f("uq_placements_game_id_player_id_snapshot_tile_id_phase"),
        "placements",
        ["game_id", "player_id", "snapshot_tile_id", "phase"],
    )
    op.create_foreign_key(
        op.f("fk_placements_player_id_game_players"),
        "placements",
        "game_players",
        ["player_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Les placements existants appartiennent tous à une place : la contrainte est déjà respectée
    op.create_check_constraint(
        op.f("ck_placements_seat_or_player"),
        "placements",
        "(participant_id IS NULL) <> (player_id IS NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Les placements des parties closes n'ont plus de place : ils ne peuvent pas revenir sur
    # participant_id NOT NULL et sont supprimés (perte des classements des parties closes)
    op.execute("DELETE FROM placements WHERE participant_id IS NULL")
    op.drop_constraint(op.f("ck_placements_seat_or_player"), "placements", type_="check")
    op.drop_constraint(
        op.f("fk_placements_player_id_game_players"), "placements", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("uq_placements_game_id_player_id_snapshot_tile_id_phase"), "placements", type_="unique"
    )
    op.drop_index(op.f("ix_placements_player_id"), table_name="placements")
    op.alter_column("placements", "participant_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("placements", "player_id")
    op.drop_index(op.f("ix_game_players_user_id"), table_name="game_players")
    op.drop_table("game_players")
