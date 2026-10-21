from app.constants.error_codes import ErrorCode


class RoomNotFoundError(Exception):
    """Salle inexistante, fermée, ou dont l'utilisateur n'est pas participant : les cas sont
    indiscernables, pour ne pas révéler l'existence d'une salle à qui n'y a pas de place."""


class RoomAdminRequiredError(Exception):
    """L'utilisateur est participant de la salle, mais pas son room admin."""


class RoomSettingsLockedError(Exception):
    """Une partie est en cours : seul le réglage des arrivées peut changer."""


class NicknameTakenError(Exception):
    """Le pseudo choisi par l'invité est déjà porté dans la salle (sans tenir compte de la
    casse), par un invité ou par un compte."""


class RoomFullError(Exception):
    """La salle a déjà le nombre maximal de places de son plan (US-2.6)."""

    def __init__(self, max_participants: int) -> None:
        super().__init__(max_participants)
        self.max_participants = max_participants


class RoomLockedError(Exception):
    """Une partie est en cours et le room admin a verrouillé les arrivées (US-2.10)."""


class GuestLinkInvalidError(Exception):
    """Lien perso inconnu, expiré ou d'une salle fermée : la place de l'invité est perdue."""


class ParticipantNotFoundError(Exception):
    """Aucune place de ce participant dans la salle (inconnu, déjà retiré, ou invité dont le
    lien a expiré)."""


class CannotRemoveRoomAdminError(Exception):
    """Le room admin a visé sa propre place : il ne peut pas se retirer de sa salle."""


class RoomBannedError(Exception):
    """Le compte, ou le navigateur de l'invité, est banni de la salle (US-2.12)."""


class BanNotFoundError(Exception):
    """Aucun bannissement de cet identifiant dans la salle."""


class ChannelClosedError(Exception):
    """Le canal temps réel doit être fermé avec ce code (4000-4999) et ce code d'erreur comme
    raison."""

    def __init__(self, close_code: int, reason: ErrorCode) -> None:
        super().__init__(close_code, reason)
        self.close_code = close_code
        self.reason = reason
