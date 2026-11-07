from app.constants.rooms import ROOM_CODE_ALPHABET, ROOM_CODE_LENGTH
from app.services.rooms import generate_room_code

CONFUSABLE_CHARACTERS: set[str] = set("0O1I")


def test_room_codes_use_only_the_unambiguous_alphabet():
    codes: list[str] = [generate_room_code() for _ in range(200)]

    assert all(len(code) == ROOM_CODE_LENGTH for code in codes)
    assert set("".join(codes)) <= set(ROOM_CODE_ALPHABET)
    assert not set("".join(codes)) & CONFUSABLE_CHARACTERS
    assert len(set(codes)) > 1
