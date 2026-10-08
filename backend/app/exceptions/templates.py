class TemplateNotFoundError(Exception):
    """Template inexistant, supprimé, ou appartenant à un autre utilisateur : les trois cas sont
    indiscernables, pour ne pas révéler l'existence des templates des autres."""
