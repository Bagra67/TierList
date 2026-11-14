class TemplateNotFoundError(Exception):
    pass


class TemplateHasNoTilesError(Exception):
    pass


class TemplateHiddenError(Exception):
    pass


class TemplateModerationConflictError(Exception):
    pass


class TierNotFoundError(Exception):
    pass


class LastTierError(Exception):
    pass


class TileNotFoundError(Exception):
    pass


class TileEmptyError(Exception):
    pass


class InvalidTagError(Exception):
    pass


class TileLimitReachedError(Exception):
    def __init__(self, max_tiles: int) -> None:
        super().__init__(max_tiles)
        self.max_tiles = max_tiles
