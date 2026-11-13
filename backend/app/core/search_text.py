import re
import unicodedata

LIGATURES: dict[int, str] = str.maketrans({"œ": "oe", "Œ": "oe", "æ": "ae", "Æ": "ae"})
NOT_SEARCHABLE: re.Pattern[str] = re.compile(r"[^0-9a-z]+")


def normalize_search_text(text: str) -> str:
    decomposed: str = unicodedata.normalize("NFKD", text.translate(LIGATURES))
    without_marks: str = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(NOT_SEARCHABLE.sub(" ", without_marks.casefold()).split())
