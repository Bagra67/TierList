import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions.templates import CannotLikeOwnTemplateError, TemplateNotFoundError
from app.models.template import Template
from app.models.user import User
from app.repositories import template_likes as like_repository
from app.repositories import templates as template_repository


@dataclass(frozen=True)
class PublicTemplate:
    template: Template
    owner_name: str
    like_count: int


@dataclass(frozen=True)
class LikeState:
    liked: bool
    like_count: int
    can_like: bool


class MarketplaceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_template(self, template_id: uuid.UUID) -> PublicTemplate:
        listed: tuple[Template, str] | None = (
            template_repository.get_listed_template_with_owner_name(
                self._session, template_id, datetime.now(UTC)
            )
        )
        if listed is None:
            raise TemplateNotFoundError
        template, owner_name = listed
        like_count: int = like_repository.count_likes(self._session, template.id)
        return PublicTemplate(template, owner_name, like_count)

    def like_state(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        return self._like_state(user, template_id, owner_id)

    def like(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        if owner_id == user.id:
            raise CannotLikeOwnTemplateError
        like_repository.add_like(self._session, template_id, user.id)
        self._session.commit()
        return self._like_state(user, template_id, owner_id)

    def unlike(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        like_repository.remove_like(self._session, template_id, user.id)
        self._session.commit()
        return self._like_state(user, template_id, owner_id)

    def list_template_updates(self, limit: int) -> list[tuple[uuid.UUID, datetime]]:
        return template_repository.list_listed_template_updates(
            self._session, datetime.now(UTC), limit
        )

    def _listed_owner_id(self, template_id: uuid.UUID) -> uuid.UUID:
        listed: tuple[str, uuid.UUID] | None = (
            template_repository.get_listed_template_name_and_owner(
                self._session, template_id, datetime.now(UTC)
            )
        )
        if listed is None:
            raise TemplateNotFoundError
        return listed[1]

    def _like_state(self, user: User, template_id: uuid.UUID, owner_id: uuid.UUID) -> LikeState:
        return LikeState(
            liked=like_repository.has_liked(self._session, template_id, user.id),
            like_count=like_repository.count_likes(self._session, template_id),
            can_like=owner_id != user.id,
        )
