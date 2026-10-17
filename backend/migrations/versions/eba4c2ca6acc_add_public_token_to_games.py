"""add public token to games

Revision ID: eba4c2ca6acc
Revises: 8cd7afa2d6eb
Create Date: 2026-10-17 15:45:35.600138

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eba4c2ca6acc"
down_revision: str | Sequence[str] | None = "8cd7afa2d6eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("games", sa.Column("public_token", sa.String(length=32), nullable=True))
    op.create_unique_constraint(op.f("uq_games_public_token"), "games", ["public_token"])
    # Les parties déjà closes reçoivent leur lien : 122 bits aléatoires (gen_random_uuid, natif
    # depuis PostgreSQL 13), en 32 caractères hexadécimaux ; les nouvelles l'ont à la clôture
    op.execute(
        "UPDATE games SET public_token = replace(gen_random_uuid()::text, '-', '') "
        "WHERE status = 'closed'"
    )
    op.create_check_constraint(
        op.f("ck_games_closed_has_public_token"),
        "games",
        "status <> 'closed' OR public_token IS NOT NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_games_closed_has_public_token"), "games", type_="check")
    op.drop_constraint(op.f("uq_games_public_token"), "games", type_="unique")
    op.drop_column("games", "public_token")
