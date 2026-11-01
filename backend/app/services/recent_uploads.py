"""Derniers envois d'images, pour la revue des super admins (US-1.7, docs/technical/moderation.md) :
repérer une image problématique avant qu'on la signale."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.image import Image, ImageStatus
from app.repositories import images as image_repository


@dataclass(frozen=True)
class RecentUpload:
    image: Image
    # None une fois le compte de l'auteur supprimé
    author_name: str | None
    # Modèles non supprimés qui montrent l'image, par ordre alphabétique
    template_names: list[str]
    # Parties jouées avec l'image, en cours ou terminées
    game_count: int


@dataclass(frozen=True)
class RecentUploadsPage:
    # Des plus récentes aux plus anciennes
    uploads: list[RecentUpload]
    # Il reste des images après cette page
    has_more: bool


class RecentUploadsService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def page(
        self,
        limit: int,
        offset: int,
        author: str | None,
        created_after: datetime | None,
        created_before: datetime | None,
        status: ImageStatus | None,
    ) -> RecentUploadsPage:
        """Les images à partir de offset, avec leur usage. Une image de plus est lue pour savoir
        s'il en reste ; les usages de toute la page sont lus en deux requêtes."""
        rows: list[tuple[Image, str | None]] = image_repository.list_recent_images(
            self._session, limit + 1, offset, author, created_after, created_before, status
        )
        page_rows: list[tuple[Image, str | None]] = rows[:limit]
        image_ids: list[uuid.UUID] = [image.id for image, _ in page_rows]
        template_names: dict[uuid.UUID, list[str]] = image_repository.template_names_by_image(
            self._session, image_ids
        )
        game_counts: dict[uuid.UUID, int] = image_repository.game_counts_by_image(
            self._session, image_ids
        )
        uploads: list[RecentUpload] = [
            RecentUpload(
                image=image,
                author_name=author_name,
                template_names=template_names.get(image.id, []),
                game_count=game_counts.get(image.id, 0),
            )
            for image, author_name in page_rows
        ]
        return RecentUploadsPage(uploads=uploads, has_more=len(rows) > limit)
