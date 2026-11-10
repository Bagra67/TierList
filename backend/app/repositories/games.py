import uuid
from datetime import datetime

from sqlalchemy import Exists, ScalarSelect, Select, func, or_, select, update
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
    return select(func.count(GamePlayer.id)).where(GamePlayer.game_id == Game.id).scalar_subquery()


def list_history(session: Session, user_id: uuid.UUID, limit: int, offset: int) -> list[Game]:
    is_player: Exists = (
        select(GamePlayer.id)
        .where(GamePlayer.game_id == Game.id, GamePlayer.user_id == user_id)
        .exists()
    )
    statement: Select[Game] = (
        select(Game)
        .where(Game.status == GameStatus.CLOSED, or_(Game.admin_id == user_id, is_player))
        .order_by(Game.closed_at.desc(), Game.id)
        .limit(limit)
        .offset(offset)
        .options(
            selectinload(Game.snapshot),
            with_expression(Game.player_count, player_count_expression()),
        )
    )
    return list(session.scalars(statement).all())


def list_closed_games_of_room(session: Session, room_id: uuid.UUID) -> list[Game]:
    statement: Select[Game] = (
        select(Game)
        .where(Game.room_id == room_id, Game.status == GameStatus.CLOSED)
        .order_by(Game.closed_at.desc(), Game.id)
        .options(
            selectinload(Game.snapshot),
            with_expression(Game.player_count, player_count_expression()),
        )
    )
    return list(session.scalars(statement).all())


def get_game(session: Session, game_id: uuid.UUID) -> Game | None:
    return session.get(Game, game_id)


def get_game_player(session: Session, player_id: uuid.UUID) -> GamePlayer | None:
    return session.get(GamePlayer, player_id)


def get_snapshot_tile(session: Session, tile_id: uuid.UUID) -> SnapshotTile | None:
    return session.get(SnapshotTile, tile_id)


def get_closed_game_by_token(session: Session, public_token: str) -> Game | None:
    statement: Select[Game] = (
        select(Game)
        .where(
            Game.public_token == public_token,
            Game.status == GameStatus.CLOSED,
            Game.hidden_at.is_(None),
        )
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
    return session.scalar(select(Game.room_id).where(Game.id == game_id))


def list_pending_round_deadlines(session: Session) -> list[tuple[uuid.UUID, int, datetime]]:
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
        if ends_at is not None:
            deadlines.append((game_id, round_number, ends_at))
    return deadlines


def list_pending_cooldown_ends(session: Session) -> list[tuple[uuid.UUID, datetime]]:
    statement: Select[uuid.UUID, datetime | None] = select(Game.id, Game.cooldown_ends_at).where(
        Game.room_id.is_not(None),
        Game.status == GameStatus.COOLDOWN,
        Game.cooldown_ends_at.is_not(None),
    )
    cooldown_ends: list[tuple[uuid.UUID, datetime]] = []
    for game_id, cooldown_ends_at in session.execute(statement):
        if cooldown_ends_at is not None:
            cooldown_ends.append((game_id, cooldown_ends_at))
    return cooldown_ends


def public_tokens_by_game(
    session: Session, game_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    statement = select(Game.id, Game.public_token).where(Game.id.in_(game_ids))
    return {game_id: token for game_id, token in session.execute(statement).all()}


def get_game_for_update(session: Session, game_id: uuid.UUID) -> Game | None:
    return session.get(Game, game_id, with_for_update=True)


def list_hidden_games(session: Session, limit: int, offset: int) -> list[Game]:
    statement: Select[Game] = (
        select(Game)
        .where(Game.hidden_at.is_not(None))
        .options(selectinload(Game.snapshot))
        .order_by(Game.hidden_at.desc(), Game.id)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement).all())


def list_guest_players_of_room(
    session: Session, room_id: uuid.UUID, nickname: str
) -> list[GamePlayer]:
    statement: Select[GamePlayer] = (
        select(GamePlayer)
        .join(Game, Game.id == GamePlayer.game_id)
        .where(
            Game.room_id == room_id,
            GamePlayer.user_id.is_(None),
            GamePlayer.display_name == nickname,
        )
    )
    return list(session.scalars(statement).all())


def rename_players_of_account(session: Session, user_id: uuid.UUID, display_name: str) -> None:
    session.execute(
        update(GamePlayer)
        .where(GamePlayer.user_id == user_id)
        .values(display_name=display_name)
        .execution_options(synchronize_session=False)
    )
