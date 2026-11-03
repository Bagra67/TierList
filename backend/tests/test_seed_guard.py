import pytest

from app.seed.guard import LOCAL_SEED_PASSWORD, SeedRefusedError, check_database, seed_password


@pytest.mark.parametrize("database_name", ["tierlist", "tierlist_staging"])
def test_the_local_and_staging_databases_can_be_seeded(database_name: str):
    check_database(database_name)


@pytest.mark.parametrize("database_name", ["tierlist_prod", "tierlist_test", "postgres", ""])
def test_every_other_database_is_refused(database_name: str):
    with pytest.raises(SeedRefusedError):
        check_database(database_name)


def test_the_local_password_is_used_without_seed_password():
    assert seed_password("tierlist", None) == LOCAL_SEED_PASSWORD


def test_seed_password_is_required_on_staging():
    with pytest.raises(SeedRefusedError):
        seed_password("tierlist_staging", None)
    assert seed_password("tierlist_staging", "a-secret") == "a-secret"
