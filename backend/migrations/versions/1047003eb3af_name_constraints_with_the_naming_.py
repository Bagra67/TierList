"""name constraints with the naming convention

Revision ID: 1047003eb3af
Revises: 21df5503e778
Create Date: 2026-10-04 19:57:23.150069

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1047003eb3af"
down_revision: str | Sequence[str] | None = "21df5503e778"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, nom donné par PostgreSQL, nom de la convention de app/db/base.py). Les index
# « ix_… » suivent déjà la convention. Renommer une clé primaire ou une contrainte d'unicité
# renomme aussi son index.
#
# Alembic applique la convention de target_metadata aux migrations précédentes : une base
# créée après l'ajout de la convention a déjà ces noms, seules les bases plus anciennes sont
# renommées.
RENAMED_CONSTRAINTS = [
    ("users", "users_pkey", "pk_users"),
    ("users", "users_email_key", "uq_users_email"),
    ("refresh_tokens", "refresh_tokens_pkey", "pk_refresh_tokens"),
    ("refresh_tokens", "refresh_tokens_token_hash_key", "uq_refresh_tokens_token_hash"),
    ("refresh_tokens", "refresh_tokens_user_id_fkey", "fk_refresh_tokens_user_id_users"),
    ("oauth_accounts", "oauth_accounts_pkey", "pk_oauth_accounts"),
    (
        "oauth_accounts",
        "oauth_accounts_provider_provider_subject_key",
        "uq_oauth_accounts_provider_provider_subject",
    ),
    ("oauth_accounts", "oauth_accounts_user_id_fkey", "fk_oauth_accounts_user_id_users"),
]


def _rename(table: str, old_name: str, new_name: str) -> None:
    exists = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM pg_constraint"
                " WHERE conrelid = CAST(:table AS regclass) AND conname = :name"
            ),
            {"table": table, "name": old_name},
        )
        .scalar()
    )
    if exists is not None:
        op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')


def upgrade() -> None:
    """Upgrade schema."""
    for table, postgres_name, convention_name in RENAMED_CONSTRAINTS:
        _rename(table, postgres_name, convention_name)


def downgrade() -> None:
    """Downgrade schema."""
    for table, postgres_name, convention_name in RENAMED_CONSTRAINTS:
        _rename(table, convention_name, postgres_name)
