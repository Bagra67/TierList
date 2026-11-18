class CannotBanSuperAdminError(Exception):
    pass


class BanEndInPastError(Exception):
    pass


class AccountNotBannedError(Exception):
    pass


class ImagesHidingInProgressError(Exception):
    pass
