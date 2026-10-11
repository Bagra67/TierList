"""add guests to participants

Revision ID: 0a183946a488
Revises: fedf7b56dfa2
Create Date: 2026-10-11 19:09:47.587992

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a183946a488"
down_revision: str | Sequence[str] | None = "fedf7b56dfa2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("participants", sa.Column("nickname", sa.String(length=50), nullable=True))
    op.add_column(
        "participants", sa.Column("guest_token_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "participants",
        sa.Column("guest_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Une place d'invité n'a pas de compte
    op.alter_column("participants", "user_id", existing_type=sa.Uuid(), nullable=True)
    op.create_unique_constraint(
        op.f("uq_participants_guest_token_hash"), "participants", ["guest_token_hash"]
    )
    # Soit un compte, soit un invité complet (pseudo, empreinte du jeton, expiration). Les places
    # existantes sont toutes des comptes : elles respectent déjà la contrainte.
    op.create_check_constraint(
        op.f("ck_participants_account_or_guest"),
        "participants",
        "(user_id IS NULL) = (nickname IS NOT NULL)"
        " AND (nickname IS NULL) = (guest_token_hash IS NULL)"
        " AND (nickname IS NULL) = (guest_expires_at IS NULL)",
    )
    # Pseudo unique dans la salle, sans tenir compte de la casse
    op.create_index(
        "uq_participants_room_id_lower_nickname",
        "participants",
        ["room_id", sa.literal_column("lower(nickname)")],
        unique=True,
        postgresql_where=sa.text("nickname IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_participants_room_id_lower_nickname", table_name="participants")
    op.drop_constraint(op.f("ck_participants_account_or_guest"), "participants", type_="check")
    op.drop_constraint(op.f("uq_participants_guest_token_hash"), "participants", type_="unique")
    # Les invités n'ont pas de compte : ils ne survivent pas au retour en arrière
    op.execute("DELETE FROM participants WHERE user_id IS NULL")
    op.alter_column("participants", "user_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("participants", "guest_expires_at")
    op.drop_column("participants", "guest_token_hash")
    op.drop_column("participants", "nickname")
