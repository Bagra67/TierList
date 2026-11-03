import logging
import random
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import User
from app.seed.accounts import SeedAccounts, create_accounts
from app.seed.cleanup import SeedCleanup, delete_seed_data
from app.seed.games import SeedGames, create_closed_games
from app.seed.moderation import (
    ban_accounts,
    create_moderation_log,
    moderate_images,
    moderate_templates,
)
from app.seed.no_op import NoOpRoomEventPublisher
from app.seed.rooms import SeedRooms, create_open_rooms
from app.seed.sizes import SeedSize
from app.seed.templates import SeedTemplates, create_templates
from app.services.image_storage import ImageStorage
from app.services.rooms import RoomService

logger = logging.getLogger(__name__)

SEED_RANDOM_SEED = 2026


@contextmanager
def _step(name: str) -> Iterator[None]:
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
        moderated_images: int = moderate_images(
            session,
            settings,
            storage,
            accounts.super_admins,
            templates.images,
            size.hidden_images,
            size.deleted_images,
            rng,
        )
        moderated_templates: int = moderate_templates(
            session,
            settings,
            accounts.super_admins,
            _templates_to_hide(played, templates, size.hidden_templates),
            rng,
        )
        banned_count: int = size.temporarily_banned_accounts + size.permanently_banned_accounts
        banned: list[User] = accounts.players[len(accounts.players) - banned_count :]
        banned_accounts: int = ban_accounts(
            session,
            settings,
            accounts.super_admins,
            banned[: size.temporarily_banned_accounts],
            banned[size.temporarily_banned_accounts :],
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
        open_rooms=len(played.open_rooms_with_past_games)
        + len(open_rooms.full)
        + len(open_rooms.with_bans),
        moderation_actions=size.moderation_actions
        + moderated_images
        + moderated_templates
        + banned_accounts,
    )


def _templates_to_hide(played: SeedGames, templates: SeedTemplates, count: int) -> list[uuid.UUID]:
    candidates: list[uuid.UUID] = [
        room.template_id
        for room in played.open_rooms_with_past_games
        if room.template_id is not None
    ]
    candidates.extend(template.id for template in templates.playable)
    return list(dict.fromkeys(candidates))[:count]
