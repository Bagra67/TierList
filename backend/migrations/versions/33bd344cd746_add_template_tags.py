"""add template tags

Revision ID: 33bd344cd746
Revises: 9b3e5d71c2a4
Create Date: 2026-11-13 20:31:50.832947

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.search_text import normalize_search_text

# revision identifiers, used by Alembic.
revision: str = "33bd344cd746"
down_revision: str | Sequence[str] | None = "9b3e5d71c2a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LISTED_TEMPLATES = "visibility = 'public' AND moderation = 'none' AND deleted_at IS NULL"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "template_tags",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_label", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=30), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_template_tags_template_id_templates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("template_id", "normalized_label", name=op.f("pk_template_tags")),
    )
    op.create_index(
        op.f("ix_template_tags_normalized_label"),
        "template_tags",
        ["normalized_label"],
        unique=False,
    )
    op.add_column(
        "templates",
        sa.Column("search_text", sa.Text(), server_default=sa.text("''"), nullable=False),
    )
    _fill_search_text()
    op.create_index(
        "ix_templates_listed_search",
        "templates",
        [sa.literal_column("to_tsvector('simple', search_text)")],
        unique=False,
        postgresql_using="gin",
        postgresql_where=sa.text(LISTED_TEMPLATES),
    )


def _fill_search_text() -> None:
    connection: sa.Connection = op.get_bind()
    templates: sa.TableClause = sa.table(
        "templates", sa.column("id", sa.Uuid()), sa.column("name"), sa.column("search_text")
    )
    rows: list[sa.Row] = list(connection.execute(sa.select(templates.c.id, templates.c.name)))
    for row in rows:
        connection.execute(
            templates.update()
            .where(templates.c.id == row.id)
            .values(search_text=normalize_search_text(row.name))
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_templates_listed_search",
        table_name="templates",
        postgresql_using="gin",
        postgresql_where=sa.text(LISTED_TEMPLATES),
    )
    op.drop_column("templates", "search_text")
    op.drop_index(op.f("ix_template_tags_normalized_label"), table_name="template_tags")
    op.drop_table("template_tags")
