"""Réglages de jeu partagés par la salle, qui les configure, et la partie, qui garde ceux du
démarrage (docs/technical/rooms.md, docs/technical/games.md)."""

from enum import StrEnum


class ItemOrder(StrEnum):
    """Ordre de passage des tuiles pendant une partie."""

    TEMPLATE = "template"
    RANDOM = "random"


class AutoAdvance(StrEnum):
    """Passage automatique à l'item suivant."""

    # Le room admin passe à l'item suivant lui-même
    NONE = "none"
    # À la fin du timer de l'item (timer_seconds)
    TIMER = "timer"
    # Quand tous les joueurs ont placé l'item
    EVERYONE_PLACED = "everyone_placed"
