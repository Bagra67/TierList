"""Création du jeu de données complet : suppression de l'ancien, puis comptes, modèles, parties
terminées, salles ouvertes et journal de modération."""

import logging
import random
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import User
from app.seed.accounts import SeedAccounts, create_accounts
from app.seed.cleanup import SeedCleanup, delete_seed_data
from app.seed.games import SeedGames, create_closed_games
from app.seed.moderation import create_moderation_log
from app.seed.no_op import NoOpRoomEventPublisher
from app.seed.rooms import SeedRooms, create_open_rooms
from app.seed.sizes import SeedSize
from app.seed.templates import SeedTemplates, create_templates
from app.services.image_storage import ImageStorage
from app.services.rooms import RoomService

logger = logging.getLogger(__name__)

# Graine fixe : le même jeu de données à chaque lancement
SEED_RANDOM_SEED = 2026


@contextmanager
def _step(name: str) -> Iterator[None]:
    """Annonce une étape et sa durée : sur staging, chaque requête traverse Internet et le
    lancement prend plusieurs minutes, le journal montre où il en est."""
    logger.info("Étape %s…", name)
    started: float = time.monotonic()
    yield
    logger.info("Étape %s terminée en %.1f s", name, time.monotonic() - started)


@dataclass(frozen=True)
class SeedSummary:
    removed: SeedCleanup
    accounts: int
    templates: int
    images: int
    closed_games: int
    open_rooms: int
    moderation_actions: int


def run_seed(
    session: Session, settings: Settings, storage: ImageStorage, size: SeedSize, password: str
) -> SeedSummary:
    rng: random.Random = random.Random(SEED_RANDOM_SEED)
    with _step("1/6 Suppression de l'ancien jeu de données"):
        removed: SeedCleanup = delete_seed_data(session, storage)
    with _step("2/6 Comptes"):
        accounts: SeedAccounts = create_accounts(session, settings, size, password)
    with _step("3/6 Modèles et images"):
        templates: SeedTemplates = create_templates(
            session, settings, storage, size, accounts.players, rng
        )

    # Personne n'est connecté aux salles : les événements temps réel ne vont nulle part
    rooms: RoomService = RoomService(session, settings, NoOpRoomEventPublisher())
    with _step("4/6 Parties terminées"):
        played: SeedGames = create_closed_games(
            session,
            settings,
            rooms,
            size,
            accounts.players,
            templates.playable,
            rng,
        )
    with _step("5/6 Salles ouvertes"):
        open_rooms: SeedRooms = create_open_rooms(
            session, settings, rooms, size, accounts.players, templates.playable, rng
        )

    moderation_targets: list[User] = [*accounts.players, *accounts.unverified, *accounts.google]
    with _step("6/6 Journal de modération"):
        create_moderation_log(
            session,
            size.moderation_actions,
            accounts.super_admins,
            moderation_targets,
            [*templates.playable, *templates.deleted],
            rng,
        )
    return SeedSummary(
        removed=removed,
        accounts=len(accounts.super_admins)
        + len(accounts.players)
        + len(accounts.unverified)
        + len(accounts.google),
        templates=len(templates.playable) + len(templates.empty) + len(templates.deleted),
        images=size.image_templates * size.image_tiles_per_template,
        closed_games=len(played.closed),
        open_rooms=len(played.lobby_rooms) + len(open_rooms.full) + len(open_rooms.with_bans),
        moderation_actions=size.moderation_actions,
    )
