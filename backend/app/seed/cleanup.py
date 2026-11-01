"""Suppression de tout ce que le jeu de données a créé, avant d'en créer un nouveau.

L'ordre compte : plusieurs liens vers les comptes sont en SET NULL (l'hôte d'une partie, son
joueur, l'auteur d'une entrée du journal, le propriétaire d'une image), et supprimer les comptes en
premier laisserait ces lignes orphelines. Les autres comptes ne sont jamais touchés."""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import Image
from app.models.moderation_action import ModerationAction
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.user import User
from app.seed.accounts import SEED_EMAIL_DOMAIN, SEED_EMAIL_PREFIX
from app.services.image_storage import ImageStorage


@dataclass(frozen=True)
class SeedCleanup:
    accounts: int
    games: int
    images: int


def delete_seed_data(session: Session, storage: ImageStorage) -> SeedCleanup:
    seed_user_ids: list[uuid.UUID] = list(
        session.scalars(
            select(User.id).where(
                User.email.startswith(SEED_EMAIL_PREFIX, autoescape=True),
                User.email.endswith(SEED_EMAIL_DOMAIN, autoescape=True),
            )
        ).all()
    )
    if not seed_user_ids:
        return SeedCleanup(accounts=0, games=0, images=0)

    # 1. Le journal : l'auteur passerait à NULL
    session.execute(delete(ModerationAction).where(ModerationAction.actor_id.in_(seed_user_ids)))
    # 2. Les parties animées ou jouées par un compte seed (tours, joueurs et placements partent
    # avec elles) : l'hôte et les joueurs passeraient à NULL
    games: int = len(
        session.scalars(
            delete(Game)
            .where(
                or_(
                    Game.admin_id.in_(seed_user_ids),
                    exists().where(
                        GamePlayer.game_id == Game.id, GamePlayer.user_id.in_(seed_user_ids)
                    ),
                )
            )
            .returning(Game.id)
        ).all()
    )
    # 3. Les instantanés des modèles seed, que plus aucune partie n'utilise : leur modèle
    # passerait à NULL
    seed_template_ids = select(Template.id).where(Template.owner_id.in_(seed_user_ids))
    session.execute(
        delete(TemplateSnapshot).where(TemplateSnapshot.template_id.in_(seed_template_ids))
    )
    # 4. Les images, relevées avant les comptes (leur propriétaire passerait à NULL), supprimées
    # après les modèles et leurs tuiles qui les désignent
    images: list[tuple[uuid.UUID, str]] = [
        (image_id, storage_key)
        for image_id, storage_key in session.execute(
            select(Image.id, Image.storage_key).where(Image.owner_id.in_(seed_user_ids))
        ).all()
    ]
    # 5. Les comptes : leurs modèles, salles, places, bannissements et sessions partent en cascade
    session.execute(delete(User).where(User.id.in_(seed_user_ids)))
    session.execute(delete(Image).where(Image.id.in_([image_id for image_id, _ in images])))
    session.commit()
    # Les fichiers après le commit : une erreur de stockage ne laisse pas d'image sans fichier
    for _, storage_key in images:
        storage.delete(storage_key)
    return SeedCleanup(accounts=len(seed_user_ids), games=games, images=len(images))
