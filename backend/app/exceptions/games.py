class GameInProgressError(Exception):
    pass


class NoPlacingParticipantError(Exception):
    pass


class RoundNotInProgressError(Exception):
    pass


class NotAPlacingParticipantError(Exception):
    pass


class ItemNotCurrentError(Exception):
    pass


class ItemNotInGameError(Exception):
    pass


class CooldownOverError(Exception):
    pass


class CooldownNotInProgressError(Exception):
    pass


class GameResultsNotFoundError(Exception):
    pass
