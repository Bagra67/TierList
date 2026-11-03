import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.image import Image, ImageStatus
from app.repositories import images as image_repository


@dataclass(frozen=True)
class RecentUpload:
    image: Image
    author_name: str | None
    template_names: list[str]
    game_count: int


@dataclass(frozen=True)
class RecentUploadsPage:
    uploads: list[RecentUpload]
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
        owner_id: uuid.UUID | None = None,
    ) -> RecentUploadsPage:
        rows: list[tuple[Image, str | None]] = image_repository.list_recent_images(
            self._session,
            limit + 1,
            offset,
            author,
            created_after,
            created_before,
            status,
            owner_id,
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
