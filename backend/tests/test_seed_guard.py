import pytest

from app.core.config import Settings
from app.seed.guard import LOCAL_SEED_PASSWORD, SeedRefusedError, check_database, seed_password
from app.seed.sizes import FULL_SIZE, SMALL_SIZE, SeedSize


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


@pytest.mark.parametrize("size", [FULL_SIZE, SMALL_SIZE])
def test_the_image_tiles_of_a_template_stay_within_the_upload_limit(size: SeedSize):
    uploads_per_hour_max: object = Settings.model_fields["image_uploads_per_hour_max"].default

    assert isinstance(uploads_per_hour_max, int)
    assert size.image_tiles_per_template <= uploads_per_hour_max
