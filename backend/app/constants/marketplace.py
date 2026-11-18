from enum import StrEnum


class MarketplaceSort(StrEnum):
    POPULAR = "popular"
    NEWEST = "newest"


MARKETPLACE_PAGE_SIZE = 24
MARKETPLACE_POPULAR_TAG_COUNT = 12
SEARCH_QUERY_MAX_LENGTH = 100
SEARCH_QUERY_MAX_WORDS = 8
