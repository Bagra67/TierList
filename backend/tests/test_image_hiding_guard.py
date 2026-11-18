import uuid

import pytest

from app.exceptions.moderation import ImagesHidingInProgressError
from app.services.image_hiding_guard import ImageHidingGuard

ALICE: uuid.UUID = uuid.uuid4()
BOB: uuid.UUID = uuid.uuid4()


def test_a_second_hiding_of_the_same_account_is_refused():
    guard: ImageHidingGuard = ImageHidingGuard()

    with guard.hold(ALICE), pytest.raises(ImagesHidingInProgressError), guard.hold(ALICE):
        pass


def test_another_account_can_be_hidden_at_the_same_time():
    guard: ImageHidingGuard = ImageHidingGuard()

    with guard.hold(ALICE), guard.hold(BOB):
        pass


def test_the_account_is_free_again_after_a_hiding_that_failed():
    guard: ImageHidingGuard = ImageHidingGuard()

    with pytest.raises(RuntimeError), guard.hold(ALICE):
        raise RuntimeError("storage unreachable")

    with guard.hold(ALICE):
        pass
