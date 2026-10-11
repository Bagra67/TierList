class TemplateNotFoundError(Exception):
    """Template inexistant, supprimé, ou appartenant à un autre utilisateur : les trois cas sont
    indiscernables, pour ne pas révéler l'existence des templates des autres."""


class TierNotFoundError(Exception):
    """Tier inexistant dans ce template (le template, lui, appartient bien à l'utilisateur)."""


class LastTierError(Exception):
    """Suppression du dernier tier : une tier list a toujours au moins un tier."""


class TileNotFoundError(Exception):
    """Tuile inexistante dans ce template (le template, lui, appartient bien à l'utilisateur)."""


class TileEmptyError(Exception):
    """La tuile n'aurait ni texte ni image : elle n'aurait aucun contenu à classer."""


class TileLimitReachedError(Exception):
    """Le template a déjà le nombre maximal de tuiles de son plan."""

    def __init__(self, max_tiles: int) -> None:
        super().__init__(max_tiles)
        self.max_tiles = max_tiles
