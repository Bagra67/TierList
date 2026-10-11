class RoomNotFoundError(Exception):
    """Salle inexistante, fermée, ou dont l'utilisateur n'est pas participant : les cas sont
    indiscernables, pour ne pas révéler l'existence d'une salle à qui n'y a pas de place."""


class RoomAdminRequiredError(Exception):
    """L'utilisateur est participant de la salle, mais pas son room admin."""


class RoomSettingsLockedError(Exception):
    """Une partie est en cours : seul le réglage des arrivées peut changer."""
