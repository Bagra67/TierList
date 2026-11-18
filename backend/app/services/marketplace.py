import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.constants.marketplace import MARKETPLACE_POPULAR_TAG_COUNT, MarketplaceSort
from app.core.cursor import decode_cursor, encode_cursor
from app.core.search_query import build_search_query
from app.core.search_text import normalize_search_text
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
class MarketplaceTemplate:
    template: Template
    owner_name: str
    like_count: int


@dataclass(frozen=True)
class MarketplacePage:
    items: list[MarketplaceTemplate]
    next_cursor: str | None


class PopularPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal[MarketplaceSort.POPULAR]
    like_count: int
    first_made_public_at: datetime
    id: uuid.UUID


class NewestPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal[MarketplaceSort.NEWEST]
    first_made_public_at: datetime
    id: uuid.UUID


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

    def list_templates(
        self,
        search: str | None,
        tag: str | None,
        sort: MarketplaceSort,
        cursor: str | None,
        limit: int,
    ) -> MarketplacePage:
        rows: list[tuple[Template, str, int]] = template_repository.list_marketplace_templates(
            self._session,
            datetime.now(UTC),
            search_query=None if search is None else build_search_query(search),
            normalized_tag=None if tag is None else normalize_search_text(tag) or None,
            sort=sort,
            after=None if cursor is None else _after(cursor, sort),
            limit=limit + 1,
        )
        items: list[MarketplaceTemplate] = [
            MarketplaceTemplate(template, owner_name, like_count)
            for template, owner_name, like_count in rows[:limit]
        ]
        next_cursor: str | None = _cursor_after(items[-1], sort) if len(rows) > limit else None
        return MarketplacePage(items=items, next_cursor=next_cursor)

    def list_popular_tags(self) -> list[str]:
        return template_repository.list_popular_listed_tags(
            self._session, datetime.now(UTC), MARKETPLACE_POPULAR_TAG_COUNT
        )

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


def _after(cursor: str, sort: MarketplaceSort) -> template_repository.MarketplaceAfter:
    if sort == MarketplaceSort.POPULAR:
        popular: PopularPosition = decode_cursor(cursor, PopularPosition)
        return template_repository.MarketplaceAfter(
            popular.like_count, popular.first_made_public_at, popular.id
        )
    newest: NewestPosition = decode_cursor(cursor, NewestPosition)
    return template_repository.MarketplaceAfter(None, newest.first_made_public_at, newest.id)


def _cursor_after(last: MarketplaceTemplate, sort: MarketplaceSort) -> str:
    first_made_public_at: datetime | None = last.template.first_made_public_at
    if first_made_public_at is None:
        raise RuntimeError("A listed template has a first publication date")
    if sort == MarketplaceSort.POPULAR:
        return encode_cursor(
            PopularPosition(
                sort=MarketplaceSort.POPULAR,
                like_count=last.like_count,
                first_made_public_at=first_made_public_at,
                id=last.template.id,
            )
        )
    return encode_cursor(
        NewestPosition(
            sort=MarketplaceSort.NEWEST,
            first_made_public_at=first_made_public_at,
            id=last.template.id,
        )
    )
