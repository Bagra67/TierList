class CannotBanSuperAdminError(Exception):
    """Un super admin ne peut jamais être banni, ni par lui-même ni par un autre super admin."""


class BanEndInPastError(Exception):
    """La fin d'un bannissement temporaire doit être dans le futur."""


class AccountNotBannedError(Exception):
    """Lever un bannissement demande un bannissement actif."""
