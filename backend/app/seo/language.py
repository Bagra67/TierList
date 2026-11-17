from operator import itemgetter
from typing import cast

from app.constants.i18n import DEFAULT_PAGE_LANGUAGE, SUPPORTED_LANGUAGES, Language

QUALITY_PARAMETER = "q="


def language_from_accept_language(header: str | None) -> Language:
    candidates: list[tuple[float, Language]] = []
    for entry in (header or "").split(","):
        tag, _, parameters = entry.partition(";")
        language: Language | None = _supported_language(tag)
        quality: float = _quality(parameters)
        if language is not None and quality > 0:
            candidates.append((quality, language))
    if not candidates:
        return DEFAULT_PAGE_LANGUAGE
    return max(candidates, key=itemgetter(0))[1]


def _supported_language(tag: str) -> Language | None:
    primary_subtag: str = tag.strip().lower().split("-")[0]
    return cast(Language, primary_subtag) if primary_subtag in SUPPORTED_LANGUAGES else None


def _quality(parameters: str) -> float:
    for parameter in parameters.split(";"):
        parameter = parameter.strip()
        if parameter.startswith(QUALITY_PARAMETER):
            try:
                return float(parameter.removeprefix(QUALITY_PARAMETER))
            except ValueError:
                return 0
    return 1
