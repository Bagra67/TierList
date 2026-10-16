"""create rooms and participants

Revision ID: fedf7b56dfa2
Revises: 7c78e9ec1be9
Create Date: 2026-10-11 14:30:15.890529

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fedf7b56dfa2"
down_revision: str | Sequence[str] | None = "7c78e9ec1be9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        # Les contraintes CHECK des valeurs (ck_rooms_room_status, ck_rooms_item_order,
        # ck_rooms_auto_advance) sont créées par les types Enum
        sa.Column(
            "status",
            sa.Enum(
                "open", "playing", name="room_status", native_enum=False, create_constraint=True
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
        sa.Column(
            "auto_advance",
            sa.Enum(
                "none",
                "timer",
                "everyone_placed",
                name="auto_advance",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("timer_seconds", sa.Integer(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("admin_plays", sa.Boolean(), nullable=False),
        sa.Column("late_arrivals_allowed", sa.Boolean(), nullable=False),
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
            ["admin_id"], ["users.id"], name=op.f("fk_rooms_admin_id_users"), ondelete="CASCADE"
        ),
        # SET NULL : la purge d'un template supprimé garde la salle
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_rooms_template_id_templates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("code", name=op.f("uq_rooms_code")),
    )
    op.create_index(op.f("ix_rooms_admin_id"), "rooms", ["admin_id"], unique=False)
    op.create_index(op.f("ix_rooms_template_id"), "rooms", ["template_id"], unique=False)
    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
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
            ["room_id"],
            ["rooms.id"],
            name=op.f("fk_participants_room_id_rooms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_participants_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_participants")),
        # Un utilisateur a au plus une place par salle ; sert aussi d'index sur room_id
        sa.UniqueConstraint("room_id", "user_id", name=op.f("uq_participants_room_id_user_id")),
    )
    op.create_index(op.f("ix_participants_user_id"), "participants", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_participants_user_id"), table_name="participants")
    op.drop_table("participants")
    op.drop_index(op.f("ix_rooms_template_id"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_admin_id"), table_name="rooms")
    op.drop_table("rooms")
