from app.constants.error_codes import ErrorCode


class RoomNotFoundError(Exception):
    pass


class RoomNotJoinedError(RoomNotFoundError):
    pass


class RoomAdminRequiredError(Exception):
    pass


class RoomSettingsLockedError(Exception):
    pass


class NicknameTakenError(Exception):
    pass


class RoomFullError(Exception):
    def __init__(self, max_participants: int) -> None:
        super().__init__(max_participants)
        self.max_participants = max_participants


class RoomLockedError(Exception):
    pass


class GuestLinkInvalidError(Exception):
    pass


class ParticipantNotFoundError(Exception):
    pass


class CannotRemoveRoomAdminError(Exception):
    pass


class RoomBannedError(Exception):
    pass


class BanNotFoundError(Exception):
    pass


class ChannelClosedError(Exception):
    def __init__(self, close_code: int, reason: ErrorCode) -> None:
        super().__init__(close_code, reason)
        self.close_code = close_code
        self.reason = reason
