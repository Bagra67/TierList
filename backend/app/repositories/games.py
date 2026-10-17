import uuid
from datetime import datetime

from sqlalchemy import Exists, ScalarSelect, Select, func, or_, select
from sqlalchemy.orm import Session, selectinload, with_expression

from app.models.enums import GameStatus
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.template_snapshot import TemplateSnapshot


def add_game(session: Session, game: Game) -> None:
    session.add(game)


def player_count_expression() -> ScalarSelect[int]:
    """Nombre de joueurs figés de la partie, pour Game.player_count (with_expression) : les listes
    de parties passées (lobby, historique) le montrent sans charger les joueurs."""
    return select(func.count(GamePlayer.id)).where(GamePlayer.game_id == Game.id).scalar_subquery()


def list_history(session: Session, user_id: uuid.UUID, limit: int, offset: int) -> list[Game]:
    """Parties closes de ce compte (US-5.5), de la plus récente à la plus ancienne : celles où il
    est un joueur figé, et celles dont il était le room admin, même sans jouer. Avec leur version
    figée (nom du template) et leur nombre de joueurs."""
    is_player: Exists = (
        select(GamePlayer.id)
        .where(GamePlayer.game_id == Game.id, GamePlayer.user_id == user_id)
        .exists()
    )
    statement: Select[Game] = (
        select(Game)
        .where(Game.status == GameStatus.CLOSED, or_(Game.admin_id == user_id, is_player))
        # L'identifiant départage deux parties closes au même instant : une page ne saute rien
        .order_by(Game.closed_at.desc(), Game.id)
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(Game.snapshot),
            with_expression(Game.player_count, player_count_expression()),
        )
    )
    return list(session.scalars(statement).all())


def get_closed_game_by_token(session: Session, public_token: str) -> Game | None:
    """Partie close de ce lien de résultats, avec tout ce que ses résultats montrent : tiers et
    tuiles de la version figée (et leur image), placements et joueurs figés, chargés en une
    requête par table (le nombre de requêtes ne dépend pas du nombre d'items)."""
    statement: Select[Game] = (
        select(Game)
        .where(Game.public_token == public_token, Game.status == GameStatus.CLOSED)
        .options(
            selectinload(Game.snapshot).selectinload(TemplateSnapshot.tiers),
            selectinload(Game.snapshot)
            .selectinload(TemplateSnapshot.tiles)
            .selectinload(SnapshotTile.image),
            selectinload(Game.placements),
            selectinload(Game.players),
        )
    )
    return session.scalars(statement).one_or_none()


def get_room_id_of_game(session: Session, game_id: uuid.UUID) -> uuid.UUID | None:
    """Salle de la partie ; None si la salle a été supprimée (la partie lui survit)."""
    return session.scalar(select(Game.room_id).where(Game.id == game_id))


def list_pending_round_deadlines(session: Session) -> list[tuple[uuid.UUID, int, datetime]]:
    """(partie, numéro du tour, fin du timer) des tours en cours qui attendent leur timer : à
    reprogrammer au démarrage du processus. Sans les parties dont la salle a été supprimée : leur
    transition ne trouverait aucune salle et ne ferait rien, à chaque démarrage."""
    statement: Select[uuid.UUID, int, datetime | None] = (
        select(Game.id, Round.number, Round.ends_at)
        .join(Round, Round.game_id == Game.id)
        .where(
            Game.room_id.is_not(None),
            Game.status == GameStatus.IN_ROUND,
            Round.number == Game.current_round_number,
            Round.ends_at.is_not(None),
            Round.ended_at.is_(None),
        )
    )
    deadlines: list[tuple[uuid.UUID, int, datetime]] = []
    for game_id, round_number, ends_at in session.execute(statement):
        # Toujours renseignée (filtre ci-dessus) ; le test la redit pour le typage
        if ends_at is not None:
            deadlines.append((game_id, round_number, ends_at))
    return deadlines


def list_pending_cooldown_ends(session: Session) -> list[tuple[uuid.UUID, datetime]]:
    """(partie, fin du cooldown) des parties dans leur cooldown final : à reprogrammer au
    démarrage du processus, sans les parties dont la salle a été supprimée."""
    statement: Select[uuid.UUID, datetime | None] = select(Game.id, Game.cooldown_ends_at).where(
        Game.room_id.is_not(None),
        Game.status == GameStatus.COOLDOWN,
        Game.cooldown_ends_at.is_not(None),
    )
    cooldown_ends: list[tuple[uuid.UUID, datetime]] = []
    for game_id, cooldown_ends_at in session.execute(statement):
        # Toujours renseignée (filtre ci-dessus) ; le test la redit pour le typage
        if cooldown_ends_at is not None:
            cooldown_ends.append((game_id, cooldown_ends_at))
    return cooldown_ends
