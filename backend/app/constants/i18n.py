from typing import Literal, get_args

Language = Literal["fr", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = get_args(Language)
DEFAULT_EMAIL_LANGUAGE: Language = "fr"
DEFAULT_PAGE_LANGUAGE: Language = "fr"
