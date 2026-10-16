from app.constants.rooms import ROOM_CODE_ALPHABET, ROOM_CODE_LENGTH
from app.services.rooms import generate_room_code


def test_room_codes_use_only_the_unambiguous_alphabet():
    codes: list[str] = [generate_room_code() for _ in range(200)]

    assert all(len(code) == ROOM_CODE_LENGTH for code in codes)
    assert set("".join(codes)) <= set(ROOM_CODE_ALPHABET)
    # Aucun caractère qu'on confond en lisant ou en dictant le code
    assert not set("".join(codes)) & set("0O1I")
    # Tirages aléatoires : 200 codes identiques trahiraient un générateur figé
    assert len(set(codes)) > 1
