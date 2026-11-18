import pytest

from app.core.search_text import normalize_search_text


@pytest.mark.parametrize(
    ("text", "normalized"),
    [
        ("Pokémon", "pokemon"),
        ("Œuvres d'Art", "oeuvres d art"),
        ("Ex-æquo", "ex aequo"),
        ("Spider-Man 2", "spider man 2"),
        ("STRAßE", "strasse"),
        ("ÇA", "ca"),
        ("café_crème", "cafe creme"),
        ("  jeux   de société  ", "jeux de societe"),
    ],
)
def test_search_text_ignores_case_accents_and_punctuation(text: str, normalized: str) -> None:
    assert normalize_search_text(text) == normalized


@pytest.mark.parametrize("text", ["日本", "!!!", "   ", ""])
def test_text_without_latin_letter_or_digit_normalizes_to_an_empty_string(text: str) -> None:
    assert normalize_search_text(text) == ""
