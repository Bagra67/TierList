LOCAL_DATABASE = "tierlist"
STAGING_DATABASE_SUFFIX = "_staging"
LOCAL_SEED_PASSWORD = "seed-password-local"


class SeedRefusedError(Exception):
    pass


def check_database(database_name: str) -> None:
    if database_name != LOCAL_DATABASE and not database_name.endswith(STAGING_DATABASE_SUFFIX):
        raise SeedRefusedError(
            f"Refusing to seed the database {database_name!r}: only {LOCAL_DATABASE!r} or "
            f"'*{STAGING_DATABASE_SUFFIX}' databases can be seeded."
        )


def seed_password(database_name: str, configured_password: str | None) -> str:
    if configured_password:
        return configured_password
    if database_name.endswith(STAGING_DATABASE_SUFFIX):
        raise SeedRefusedError("SEED_PASSWORD is required to seed a staging database.")
    return LOCAL_SEED_PASSWORD
