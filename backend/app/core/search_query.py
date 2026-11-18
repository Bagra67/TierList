from app.core.search_text import normalize_search_text

ALTERNATIVE_SEPARATOR = "|"
PREFIX_MATCH = ":*"


def search_words(raw: str) -> list[list[str]]:
    alternatives: list[list[str]] = []
    for part in raw.split(ALTERNATIVE_SEPARATOR):
        words: list[str] = normalize_search_text(part).split()
        if words:
            alternatives.append(words)
    return alternatives


def build_search_query(raw: str) -> str | None:
    alternatives: list[str] = [
        "(" + " & ".join(f"{word}{PREFIX_MATCH}" for word in words) + ")"
        for words in search_words(raw)
    ]
    return " | ".join(alternatives) if alternatives else None
