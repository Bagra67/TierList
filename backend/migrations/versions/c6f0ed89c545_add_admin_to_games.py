"""add admin to games

Revision ID: c6f0ed89c545
Revises: eba4c2ca6acc
Create Date: 2026-10-17 16:53:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6f0ed89c545"
down_revision: str | Sequence[str] | None = "eba4c2ca6acc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("games", sa.Column("admin_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_games_admin_id"), "games", ["admin_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_games_admin_id_users"),
        "games",
        "users",
        ["admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Les parties existantes reprennent le room admin de leur salle, si elle existe encore ; une
    # partie dont la salle a été fermée reste sans room admin (dans l'historique de ses joueurs)
    op.execute(
        "UPDATE games SET admin_id = rooms.admin_id FROM rooms WHERE rooms.id = games.room_id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_games_admin_id_users"), "games", type_="foreignkey")
    op.drop_index(op.f("ix_games_admin_id"), table_name="games")
    op.drop_column("games", "admin_id")
