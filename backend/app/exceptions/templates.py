class TemplateNotFoundError(Exception):
    """Template inexistant, supprimé, ou appartenant à un autre utilisateur : les trois cas sont
    indiscernables, pour ne pas révéler l'existence des templates des autres."""


class TierNotFoundError(Exception):
    """Tier inexistant dans ce template (le template, lui, appartient bien à l'utilisateur)."""


class LastTierError(Exception):
    """Suppression du dernier tier : une tier list a toujours au moins un tier."""
