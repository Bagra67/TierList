from app.models.game import Game
from app.schemas.rooms import PastGameResponse


def past_games_response(games: list[Game]) -> list[PastGameResponse]:
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
