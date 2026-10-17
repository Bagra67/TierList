class GameInProgressError(Exception):
    """La salle a déjà une partie en cours : au plus une à la fois (invariant 3)."""


class NoPlacingParticipantError(Exception):
    """Personne ne placerait les items : il faut au moins un participant qui place, le room admin
    compris s'il joue (US-3.1)."""


class RoundNotInProgressError(Exception):
    """Aucun tour n'est en cours dans la salle : pas de partie, ou plus de tour à placer."""


class NotAPlacingParticipantError(Exception):
    """Le participant ne place pas les items : le room admin qui ne joue pas (US-3.5)."""


class ItemNotCurrentError(Exception):
    """La tuile n'est pas l'item du tour en cours : un item passé ne bouge pas avant le cooldown
    (US-3.3), un item futur n'est pas encore montré."""


class ItemNotInGameError(Exception):
    """Pendant le cooldown : la tuile n'est pas un item de la partie."""


class CooldownOverError(Exception):
    """Le cooldown final est fini (sa fin est passée, son timer va clore la partie) : plus rien
    ne se place."""


class CooldownNotInProgressError(Exception):
    """La partie de la salle n'est pas dans son cooldown final : rien à terminer."""


class GameResultsNotFoundError(Exception):
    """Aucune partie close n'a ce lien de résultats (US-5.3)."""
