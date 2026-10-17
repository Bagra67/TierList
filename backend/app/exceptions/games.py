class GameInProgressError(Exception):
    """La salle a déjà une partie en cours : au plus une à la fois (invariant 3)."""


class NoPlacingParticipantError(Exception):
    """Personne ne placerait les items : il faut au moins un participant qui place, le room admin
    compris s'il joue (US-3.1)."""
