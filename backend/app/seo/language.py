from app.constants.i18n import DEFAULT_PAGE_LANGUAGE, SUPPORTED_LANGUAGES, Language

QUALITY_PARAMETER = "q="


def language_from_accept_language(header: str | None) -> Language:
    if not header:
        return DEFAULT_PAGE_LANGUAGE
    candidates: list[tuple[float, int, Language]] = []
    for position, entry in enumerate(header.split(",")):
        tag, _, parameters = entry.partition(";")
        language: Language | None = _supported_language(tag)
        quality: float = _quality(parameters)
        if language is not None and quality > 0:
            candidates.append((-quality, position, language))
    return min(candidates)[2] if candidates else DEFAULT_PAGE_LANGUAGE


def _supported_language(tag: str) -> Language | None:
    primary_subtag: str = tag.strip().lower().split("-")[0]
    for language in SUPPORTED_LANGUAGES:
        if language == primary_subtag:
            return language
    return None


def _quality(parameters: str) -> float:
    for parameter in parameters.split(";"):
        parameter = parameter.strip()
        if parameter.startswith(QUALITY_PARAMETER):
            try:
                return float(parameter.removeprefix(QUALITY_PARAMETER))
            except ValueError:
                return 0
    return 1
