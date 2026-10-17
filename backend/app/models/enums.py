"""Énumérations partagées par plusieurs modèles, schémas ou services : les statuts de la salle
et de la partie, et les réglages de jeu que la salle configure et que la partie garde au
démarrage (docs/technical/rooms.md, docs/technical/games.md)."""

from enum import StrEnum


class RoomStatus(StrEnum):
    """Une salle fermée n'est pas gardée (docs/product/milestone-1/lifecycles.md) : elle est
    supprimée, il n'y a donc pas de statut « fermée »."""

    OPEN = "open"
    # Une partie est en cours : les réglages sont bloqués, sauf les arrivées
    PLAYING = "playing"


class GameStatus(StrEnum):
    """Cycle de vie d'une partie (docs/product/milestone-1/lifecycles.md)."""

    # Un item est montré, les participants le placent
    IN_ROUND = "in_round"
    # Après le dernier tour : chacun peut tout déplacer à nouveau (#96)
    COOLDOWN = "cooldown"
    # Finale : plus rien ne change (#98)
    CLOSED = "closed"


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


class PlacementPhase(StrEnum):
    """Moment où un placement est fait (docs/product/milestone-1/domain-model.md)."""

    # Pendant le tour de l'item : le « hot take », peut être absent
    ROUND = "round"
    # Pendant le cooldown final (#96) : jamais absent, sert aux résultats
    FINAL = "final"
