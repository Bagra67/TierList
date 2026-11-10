from app.constants.moderation import HIDE_ALL_IMAGES_BATCH_SIZE
from app.models.user import User
from app.seed.sizes import FULL_SIZE
from app.seed.templates import _image_owner


def test_the_full_seed_has_an_account_with_several_batches_of_images_to_hide():
    bulk_uploader_images: int = (
        FULL_SIZE.bulk_uploader_image_templates * FULL_SIZE.image_tiles_per_template
    )
    removed_at_most: int = FULL_SIZE.hidden_images + FULL_SIZE.deleted_images

    assert bulk_uploader_images - removed_at_most > HIDE_ALL_IMAGES_BATCH_SIZE


def test_the_first_image_templates_share_one_owner_and_the_next_ones_rotate():
    owners: list[User] = [User(display_name=name) for name in ("Max", "Lou", "Zoé")]

    image_owners: list[str] = [_image_owner(owners, index, 2).display_name for index in range(4)]

    assert image_owners == ["Max", "Max", "Lou", "Zoé"]
