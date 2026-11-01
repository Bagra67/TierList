"""Garde-fous du jeu de données : jamais sur la production, et jamais avec un mot de passe connu
sur un site public."""

# Base locale (compose.yaml) ; les bases de staging finissent par _staging
LOCAL_DATABASE = "tierlist"
STAGING_DATABASE_SUFFIX = "_staging"
# Mot de passe des comptes seed en local seulement : il est écrit dans le dépôt
LOCAL_SEED_PASSWORD = "seed-password-local"


class SeedRefusedError(Exception):
    """Le jeu de données ne doit pas être créé sur cette base, ou pas avec ce mot de passe."""


def check_database(database_name: str) -> None:
    """Refuse toute base qui n'est ni la base locale ni une base de staging : la production en
    particulier (tierlist_prod), même par erreur."""
    if database_name != LOCAL_DATABASE and not database_name.endswith(STAGING_DATABASE_SUFFIX):
        raise SeedRefusedError(
            f"Refusing to seed the database {database_name!r}: only {LOCAL_DATABASE!r} or "
            f"'*{STAGING_DATABASE_SUFFIX}' databases can be seeded."
        )


def seed_password(database_name: str, configured_password: str | None) -> str:
    """Mot de passe des comptes seed. Obligatoire sur staging (SEED_PASSWORD) : le site est
    public, un mot de passe écrit dans le dépôt donnerait à n'importe qui un compte super admin."""
    if configured_password:
        return configured_password
    if database_name.endswith(STAGING_DATABASE_SUFFIX):
        raise SeedRefusedError("SEED_PASSWORD is required to seed a staging database.")
    return LOCAL_SEED_PASSWORD
