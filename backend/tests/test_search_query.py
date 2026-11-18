import pytest

from app.core.search_query import build_search_query, search_words


@pytest.mark.parametrize(
    ("raw", "query"),
    [
        ("poké star", "(poke:* & star:*)"),
        ("mario film | zelda", "(mario:* & film:*) | (zelda:*)"),
        ("a & b ! c:*", "(a:* & b:* & c:*)"),
        ("Pokémon |", "(pokemon:*)"),
        ("|", None),
        ("   ", None),
    ],
)
def test_the_search_query_is_built_from_normalized_words(raw: str, query: str | None):
    assert build_search_query(raw) == query


def test_the_search_words_are_grouped_by_alternative():
    assert search_words("Spider-Man 2 | Œuvres") == [["spider", "man", "2"], ["oeuvres"]]
