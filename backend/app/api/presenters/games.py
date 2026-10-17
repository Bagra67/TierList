"""Parties closes montrées en liste : les parties passées du lobby, l'historique d'un compte."""

from app.models.game import Game
from app.schemas.rooms import PastGameResponse


def past_games_response(games: list[Game]) -> list[PastGameResponse]:
    """Les parties closes avec leur lien de résultats. Une partie close a toujours son lien et sa
    date (ck_games_closed_has_public_token) : une ligne qui ne les aurait pas est écartée plutôt
    que montrée avec un lien cassé. player_count est calculé par la requête (with_expression)."""
    past_games: list[PastGameResponse] = []
    for game in games:
        if game.public_token is None or game.closed_at is None:
            continue
        past_games.append(
            PastGameResponse(
                public_token=game.public_token,
                template_name=game.snapshot.name,
                closed_at=game.closed_at,
                player_count=game.player_count or 0,
            )
        )
    return past_games
